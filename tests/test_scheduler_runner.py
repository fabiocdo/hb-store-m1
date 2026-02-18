from __future__ import annotations

from typing import Callable

import pytest

from homebrew_cdn_m1_server.application.scheduler import apscheduler_runner as module
from homebrew_cdn_m1_server.application.scheduler.apscheduler_runner import (
    APSchedulerRunner,
)


class _FakeScheduler:
    def __init__(self) -> None:
        self.jobs: list[tuple[Callable[[], object], object | str | None, dict[str, object]]] = []
        self.started: bool = False
        self.shutdown_wait: bool | None = None

    def add_job(
        self,
        func: Callable[[], object],
        trigger: object | str | None = None,
        **kwargs: object,
    ) -> object:
        self.jobs.append((func, trigger, kwargs))
        return object()

    def start(self) -> None:
        self.started = True

    def shutdown(self, wait: bool = True) -> None:
        self.shutdown_wait = wait


def _build_runner(monkeypatch: pytest.MonkeyPatch) -> tuple[APSchedulerRunner, _FakeScheduler]:
    fake = _FakeScheduler()

    def _factory() -> _FakeScheduler:
        return fake

    monkeypatch.setattr(module, "BackgroundScheduler", _factory)
    return APSchedulerRunner(), fake


def test_scheduler_runner_given_invalid_cron_when_schedule_then_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner, _ = _build_runner(monkeypatch)
    with pytest.raises(ValueError, match="5 fields"):
        runner.schedule_cron("job", "*/5 * *", lambda: None)


def test_scheduler_runner_given_interval_and_cron_when_scheduled_then_adds_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner, fake = _build_runner(monkeypatch)

    runner.schedule_interval("int", 0, lambda: None)
    runner.schedule_cron("cron", "*/5 * * * *", lambda: None)

    assert len(fake.jobs) == 2
    _, trigger0, kwargs0 = fake.jobs[0]
    assert trigger0 == "interval"
    assert kwargs0["id"] == "int"
    assert kwargs0["seconds"] == 1
    assert kwargs0["replace_existing"] is True

    _, trigger1, kwargs1 = fake.jobs[1]
    assert trigger1 == "cron"
    assert kwargs1["id"] == "cron"
    assert kwargs1["minute"] == "*/5"
    assert kwargs1["hour"] == "*"
    assert kwargs1["day"] == "*"
    assert kwargs1["month"] == "*"
    assert kwargs1["day_of_week"] == "*"


def test_scheduler_runner_given_start_and_shutdown_when_called_then_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner, fake = _build_runner(monkeypatch)

    runner.start()
    runner.shutdown()

    assert fake.started is True
    assert fake.shutdown_wait is False

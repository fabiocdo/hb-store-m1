from __future__ import annotations

import runpy

import pytest

from homebrew_cdn_m1_server.application import app as app_module


def test_main_given_worker_exit_code_when_run_then_raises_system_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run_from_env(_cls: type[app_module.WorkerApp]) -> int:
        return 23

    monkeypatch.setattr(
        app_module.WorkerApp,
        "run_from_env",
        classmethod(_fake_run_from_env),
    )

    with pytest.raises(SystemExit) as exc:
        _ = runpy.run_module("homebrew_cdn_m1_server.__main__", run_name="__main__")

    assert exc.value.code == 23

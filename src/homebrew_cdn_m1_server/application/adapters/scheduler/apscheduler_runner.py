from __future__ import annotations

from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from homebrew_cdn_m1_server.domain.protocols.scheduler_port import SchedulerPort


class APSchedulerRunner(SchedulerPort):
    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler()

    def schedule_interval(
        self, job_id: str, seconds: int, func: Callable[[], object]
    ) -> None:
        self._scheduler.add_job(
            func,
            "interval",
            id=job_id,
            seconds=max(1, int(seconds)),
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    def schedule_cron(
        self, job_id: str, cron_expression: str, func: Callable[[], object]
    ) -> None:
        trigger = CronTrigger.from_crontab(cron_expression)
        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    def start(self) -> None:
        self._scheduler.start()

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)

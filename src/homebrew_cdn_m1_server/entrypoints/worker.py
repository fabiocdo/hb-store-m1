from __future__ import annotations

import logging
import os
import signal
import time
from pathlib import Path

from homebrew_cdn_m1_server.bootstrap.container import Container
from homebrew_cdn_m1_server.config.logging_setup import configure_logging
from homebrew_cdn_m1_server.config.settings_loader import SettingsLoader
from homebrew_cdn_m1_server.infrastructure.scheduler.apscheduler_runner import APSchedulerRunner


def main() -> int:
    settings_file = os.getenv("SETTINGS_FILE")
    config = SettingsLoader.load(Path(settings_file) if settings_file else None)

    configure_logging(config.user.log_level, config.paths.logs_dir / "app_errors.log")
    log = logging.getLogger("homebrew_cdn_m1_server.worker")

    container = Container(config)
    container.initialize()
    reconcile = container.build_reconcile_use_case()

    # Run one immediate cycle on startup.
    reconcile()

    scheduler = APSchedulerRunner()
    cron_expr = (config.user.watcher_cron_expression or "").strip()
    if cron_expr:
        scheduler.schedule_cron("reconcile", cron_expr, reconcile)
        log.info("Agendador configurado com cron: '%s'", cron_expr)
    else:
        scheduler.schedule_interval(
            "reconcile", config.watcher_interval_seconds, reconcile
        )
        log.info(
            "Agendador configurado com intervalo de %ss",
            config.watcher_interval_seconds,
        )

    scheduler.start()
    log.info("Servico iniciado")

    should_stop = False

    def _stop_handler(_signum: int, _frame) -> None:
        nonlocal should_stop
        should_stop = True

    signal.signal(signal.SIGTERM, _stop_handler)
    signal.signal(signal.SIGINT, _stop_handler)

    while not should_stop:
        time.sleep(0.5)

    scheduler.shutdown()
    log.info("Servico finalizado")
    return 0

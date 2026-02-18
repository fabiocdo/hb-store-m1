from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from homebrew_cdn_m1_server.config.logging_setup import configure_logging


def test_configure_logging_given_level_and_path_when_called_then_sets_handlers(
    temp_workspace: Path,
) -> None:
    error_log_path = temp_workspace / "data" / "internal" / "logs" / "app_errors.log"
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    try:
        root.addHandler(logging.NullHandler())
        configure_logging("info", error_log_path)

        assert error_log_path.parent.exists() is True
        assert root.level == logging.INFO
        assert len(root.handlers) == 2
        assert any(isinstance(handler, RotatingFileHandler) for handler in root.handlers)
    finally:
        root.handlers.clear()
        root.handlers.extend(original_handlers)
        root.setLevel(original_level)


def test_configure_logging_given_apscheduler_record_when_filters_applied_then_demotes_info_to_debug(
    temp_workspace: Path,
) -> None:
    error_log_path = temp_workspace / "data" / "internal" / "logs" / "app_errors.log"
    configure_logging("info", error_log_path)

    record = logging.LogRecord(
        name="apscheduler.scheduler",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    logger = logging.getLogger("apscheduler.scheduler")
    for filter_obj in logger.filters:
        if isinstance(filter_obj, logging.Filter):
            _ = filter_obj.filter(record)

    assert record.levelno == logging.DEBUG
    assert record.levelname == "DEBUG"

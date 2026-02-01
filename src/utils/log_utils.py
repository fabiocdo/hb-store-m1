import logging
import os
import time


class Logger:
    """
    Logger class with modular tagging and color support.
    """

    LOG_SETTINGS = {
        "debug": {
            "level": logging.DEBUG,
            "color": "\033[0;37m",
            "prefix": "",
        },
        "info": {
            "level": logging.INFO,
            "color": "\033[0m",
            "prefix": "",
        },
        "warn": {
            "level": logging.WARNING,
            "color": "\033[0;33m",
            "prefix": "",
        },
        "error": {
            "level": logging.ERROR,
            "color": "\033[0;31m",
            "prefix": "",
        },
    }

    MODULE_COLORS = {
        "AUTO_INDEXER": "\033[0;92m",
        "AUTO_SORTER": "\033[0;93m",
        "AUTO_FORMATTER": "\033[1;94m",
    }

    def __init__(self, name=None, log_level="info"):
        self.logger = logging.getLogger(name)
        self.worker_label = None
        self.log_level = log_level.lower()
        self._setup_logging()

    def _resolve_log_level(self, level_name):
        mapping = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warn": logging.WARNING,
            "warning": logging.WARNING,
            "error": logging.ERROR,
        }
        return mapping.get(level_name, logging.INFO)

    def _setup_logging(self):
        resolved_level = self._resolve_log_level(self.log_level)
        if not self.logger.handlers:
            logging.basicConfig(
                level=resolved_level,
                format="%(asctime)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            self.logger.setLevel(resolved_level)

    def set_worker_label(self, label):
        self.worker_label = label

    def clear_worker_label(self):
        self.worker_label = None

    def _module_tag(self, module):
        if not module:
            return ""
        label = self.worker_label
        display = f"{module}-{label}" if label else module
        base = module.split("-", 1)[0]
        module_color = self.MODULE_COLORS.get(base, "")
        if module_color:
            return f"{module_color}[{display}]\033[0m "
        return f"[{display}] "

    def log(self, action, message, module=None):
        target_level = action.lower()
        if target_level == "warn":
            target_level = "warning"

        current_numeric = self._resolve_log_level(self.log_level)
        msg_numeric = self._resolve_log_level(target_level)

        if msg_numeric < current_numeric:
            return

        settings = self.LOG_SETTINGS.get(action, self.LOG_SETTINGS["info"])
        level = settings["level"]
        prefix = settings["prefix"]
        color = settings["color"]
        module_tag = self._module_tag(module)
        sep = " " if prefix else ""
        message_text = f"{color}{prefix}{sep}{message}\033[0m"
        self.logger.log(level, f"{module_tag}{message_text}")

    def format_log_line(self, message, module=None):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        label = self.worker_label
        display = f"{module}-{label}" if module and label else module
        module_tag = f"[{display}] " if display else ""
        return f"{timestamp} {module_tag}{message}"

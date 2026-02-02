import datetime
import os

class Logger:
    """
    Logger class with modular tagging and color support.

    Provides a centralized logging mechanism that supports different severity levels
    and modular tags with colorized output for better readability in the terminal.
    """

    def __init__(self, log_level="info"):
        """
        Initialize the Logger with a name and a minimum log level.

        :param log_level: Minimum severity level to log ("debug", "info", "warn", "error")
        """
        self.levels = {
            "debug": 0,
            "info": 1,
            "warn": 2,
            "error": 3
        }
        self.log_level = self.levels.get(log_level.lower(), 1)
        
        # ANSI Color Codes
        self.colors = {
            "AUTO_INDEXER": "\033[1;92m",   # Green
            "AUTO_SORTER": "\033[1;93m",    # Yellow
            "AUTO_FORMATTER": "\033[1;94m", # Blue
            "WATCHER": "\033[1;95m",        # Purple
            "RESET": "\033[0m"
        }

        self.level_colors = {
            "debug": "\033[0;90m",  # Gray
            "info": "\033[0;97m",   # White
            "warn": "\033[0;33m",   # Orange/Yellow
            "error": "\033[0;31m"   # Red
        }

    def log(self, level, action, message=None, module=None):
        """
        Emit a log message if its level is greater than or equal to the configured log level.

        The output format is: <timestamp UTC> | [module] action: message

        :param level: Severity level ("debug", "info", "warn", "error")
        :param action: The main action or event being logged
        :param message: Optional detailed message or context
        :param module: Optional module tag (e.g., "WATCHER", "AUTO_FORMATTER")
        """
        level_val = self.levels.get(level.lower(), 1)
        if level_val >= self.log_level:
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            module_color = self.colors.get(module, "") if module else ""
            level_color = self.level_colors.get(level.lower(), "")
            reset = self.colors["RESET"]
            
            module_str = f"{module_color}[{module}]{reset} " if module else ""
            msg_str = f": {message}" if message else ""
            
            print(f"{timestamp} | {module_str}{level_color}{action}{msg_str}{reset}")


_LOGGER = None


def _get_logger() -> Logger:
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = Logger(os.environ["LOG_LEVEL"])
    return _LOGGER


def log(level, action, message=None, module=None):
    _get_logger().log(level, action, message=message, module=module)

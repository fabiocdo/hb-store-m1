import logging

LOGGER_NAME = "auto_indexer"
COLORS = {
    "created": "\033[0;32m",
    "modified": "\033[0;33m",
    "deleted": "\033[0;31m",
    "error": "\033[1;95m",
    "info": "\033[0m",
    "default": "\033[0m",
}
LOG_LEVELS = {
    "created": logging.INFO,
    "modified": logging.INFO,
    "deleted": logging.INFO,
    "error": logging.ERROR,
    "info": logging.INFO,
}
LOG_PREFIXES = {
    "created": "[+]",
    "modified": "[*]",
    "deleted": "[-]",
    "error": "[!]",
    "info": "[·]",
}

def _get_logger():
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    return logger

def log(action, message):
    logger = _get_logger()
    level = LOG_LEVELS.get(action, logging.INFO)
    prefix = LOG_PREFIXES.get(action, "[*]")
    color = COLORS.get(action, COLORS["default"])
    logger.log(level, f"{color}{prefix} {message}\033[0m")

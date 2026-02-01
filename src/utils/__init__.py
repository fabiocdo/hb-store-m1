from .log_utils import Logger
from .pkg_utils import PkgUtils

# Default Logger instance for compatibility
_default_logger = Logger()
log = _default_logger.log
set_worker_label = _default_logger.set_worker_label
clear_worker_label = _default_logger.clear_worker_label
format_log_line = _default_logger.format_log_line

# Default PkgUtils instance
pkg_utils = PkgUtils()

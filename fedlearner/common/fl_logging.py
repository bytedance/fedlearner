import os
import logging as _logging
import threading

BASIC_FORMAT = "%(asctime)s [%(levelname)s]: %(message)s " \
               "(%(filename)s:%(lineno)d)"
DEBUG = "debug"
INFO = "info"
WARN = "warn"
WARNING = "warning"
ERROR = "error"
CRITICAL = "critical"

_name_to_level = {
    DEBUG: _logging.DEBUG,
    INFO: _logging.INFO,
    WARNING: _logging.WARNING,
    WARN: _logging.WARN,
    ERROR: _logging.ERROR,
    CRITICAL: _logging.CRITICAL,
}

_logger = None
_logger_lock = threading.Lock()

def _get_level_from_env():
    level = os.getenv("FL_LOG_LEVEL", "").lower()
    return _name_to_level.get(level)

def _create_logger():
    logger = _logging.getLogger(name="fedlearner")
    if logger.handlers:
        return logger
    logger.propagate = False

    handler = _logging.StreamHandler()
    handler.setFormatter(_logging.Formatter(BASIC_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(_get_level_from_env() or _logging.INFO)

    return logger

def get_logger():
  global _logger
  if _logger:
    return _logger

  with _logger_lock:
    if _logger:
      return _logger
    _logger = _create_logger()

  return _logger

def _kwargs_add_stacklevel(kwargs, level=1):
  kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + level
  return kwargs

def set_level(level : str):
    l = _name_to_level.get(level.lower(), None)
    if not l:
        raise ValueError("unknow log level: %s"%level)
    get_logger().setLevel(l)

def critical(msg, *args, **kwargs):
  get_logger().critical(msg, args, kwargs)

def fatal(msg, *args, **kwargs):
  get_logger().fatal(msg, *args, **_kwargs_add_stacklevel(kwargs))

def error(msg, *args, **kwargs):
  get_logger().error(msg, *args, **_kwargs_add_stacklevel(kwargs))

def warning(msg, *args, **kwargs):
  get_logger().warning(msg, *args, **_kwargs_add_stacklevel(kwargs))

def warn(msg, *args, **kwargs):
  get_logger().warn(msg, *args, **_kwargs_add_stacklevel(kwargs))

def info(msg, *args, **kwargs):
  get_logger().info(msg, *args, **_kwargs_add_stacklevel(kwargs))

def debug(msg, *args, **kwargs):
  get_logger().debug(msg, *args, **_kwargs_add_stacklevel(kwargs))

def log(level, msg, *args, **kwargs):
  get_logger().log(level, msg, *args, **_kwargs_add_stacklevel(kwargs))
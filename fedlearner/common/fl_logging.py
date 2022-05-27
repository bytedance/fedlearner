# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import logging as _logging

BASIC_FORMAT = "%(asctime)s [%(levelname)s]: %(message)s " \
               "(%(filename)s:%(lineno)d)"
DEBUG = "debug"
INFO = "info"
WARNING = "warning"
ERROR = "error"
CRITICAL = "critical"

_name_to_level = {
    DEBUG: _logging.DEBUG,
    INFO: _logging.INFO,
    WARNING: _logging.WARNING,
    "warn": _logging.WARNING,
    ERROR: _logging.ERROR,
    CRITICAL: _logging.CRITICAL,
}

def _get_level_from_env():
    level_name = os.getenv("FL_LOG_LEVEL", "").lower()
    if level_name in _name_to_level:
        return _name_to_level[level_name]

    verbosity = os.getenv("VERBOSITY")
    if verbosity == "0":
        return _logging.WARNING
    if verbosity == "1":
        return _logging.INFO
    if verbosity == "2":
        return _logging.DEBUG

    return None

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

_logger = _create_logger()


def set_level(level):
    level_ = _name_to_level.get(level.lower(), None)
    if not level_:
        raise ValueError("Unknow log level: %s"%level)
    _logger.setLevel(level_)

def _kwargs_add_stack_level(kwargs):
    kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
    return kwargs

def critical(msg, *args, **kwargs):
    _logger.critical(msg, *args, **_kwargs_add_stack_level(kwargs))

def fatal(msg, *args, **kwargs):
    _logger.fatal(msg, *args, **_kwargs_add_stack_level(kwargs))

def error(msg, *args, **kwargs):
    _logger.error(msg, *args, **_kwargs_add_stack_level(kwargs))

def exception(msg, *args, **kwargs):
    _logger.exception(msg, *args, **_kwargs_add_stack_level(kwargs))

def warning(msg, *args, **kwargs):
    _logger.warning(msg, *args, **_kwargs_add_stack_level(kwargs))

def warn(msg, *args, **kwargs):
    _logger.warning(msg, *args, **_kwargs_add_stack_level(kwargs))

def info(msg, *args, **kwargs):
    _logger.info(msg, *args, **_kwargs_add_stack_level(kwargs))

def debug(msg, *args, **kwargs):
    _logger.debug(msg, *args, **_kwargs_add_stack_level(kwargs))

def log(level, msg, *args, **kwargs):
    _logger.log(msg, level, *args, **_kwargs_add_stack_level(kwargs))

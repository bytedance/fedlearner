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

critical = _logger.critical
fatal = _logger.critical
error = _logger.error
exception = _logger.exception
warning = _logger.warning
warn = _logger.warning
info = _logger.info
debug = _logger.debug
log = _logger.log

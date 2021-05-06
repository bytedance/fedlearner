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

import logging as _logging
from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG # pylint: disable=unused-import

BASIC_FORMAT = "%(asctime)s [%(levelname)s]: %(message)s " \
               "(%(filename)s:%(lineno)d)"

def _create_logger():
    logger = _logging.getLogger(name="fedlearner_trainer")
    if logger.handlers:
        return logger

    logger.propagate = False

    logger.setLevel(INFO)

    handler = _logging.StreamHandler()
    handler.setFormatter(_logging.Formatter(BASIC_FORMAT))
    logger.addHandler(handler)

    return logger

_logger = _create_logger()

def set_level(level):
    """
    Set logger level.
    """
    _logger.setLevel(level)


critical = _logger.critical
fatal = _logger.critical
error = _logger.error
exception = _logger.exception
warning = _logger.warning
warn = _logger.warning
info = _logger.info
debug = _logger.debug
log = _logger.log

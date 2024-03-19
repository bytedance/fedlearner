# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
from logging import LogRecord
from typing import Optional
import os

LOGGING_LEVEL = os.environ.get('LOGGING_LEVEL', 'INFO')


class LevelFilter(logging.Filter):

    def filter(self, record: LogRecord):
        if record.levelno <= logging.WARNING:
            return False
        return True


def logging_config(role: str, log_file: Optional[str] = None):
    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers:
        logging.root.removeHandler(handler)

    logging_format = f'%(asctime)s %(levelname)-7s [{role}]  %(message)s'
    logging.basicConfig(level=LOGGING_LEVEL, format=logging_format)
    logging.getLogger('urllib3.connectionpool').addFilter(LevelFilter())
    if log_file is not None:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(LOGGING_LEVEL)
        file_handler.setFormatter(logging.Formatter(logging_format))
        logging.getLogger().addHandler(file_handler)

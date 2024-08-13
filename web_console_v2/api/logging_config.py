# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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

# coding: utf-8

import os

from envs import Envs

root_file_path = os.path.join(Envs.FEDLEARNER_WEBCONSOLE_LOG_DIR, 'root.log')

_extra_handlers = {}


def set_extra_handlers(handlers: dict):
    """Sets extra handlers for logger.

    Incremental configurations are hard, so we keep LOGGING_CONFIG
    as the source of truth and inject extra handlers."""
    global _extra_handlers  # pylint:disable=global-statement
    _extra_handlers = handlers


def get_logging_config():
    return {
        'version':
            1,
        'disable_existing_loggers':
            False,
        'root': {
            'handlers': ['console', 'root_file'] + list(_extra_handlers.keys()),
            'level': Envs.LOG_LEVEL
        },
        'filters': {
            'requestIdFilter': {
                '()': 'fedlearner_webconsole.middleware.log_filter.RequestIdLogFilter'
            }
        },
        'handlers':
            dict(
                {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': 'generic',
                        'filters': ['requestIdFilter']
                    },
                    'root_file': {
                        'class': 'logging.handlers.TimedRotatingFileHandler',
                        'formatter': 'generic',
                        'filename': root_file_path,
                        'when': 'D',
                        'interval': 1,
                        'backupCount': 7,
                        'filters': ['requestIdFilter']
                    }
                }, **_extra_handlers),
        'formatters': {
            'generic': {
                'format': '%(asctime)s [%(process)d] [%(request_id)s] [%(levelname)s] %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
                'class': 'logging.Formatter'
            }
        }
    }

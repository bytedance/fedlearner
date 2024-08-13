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

import os
from typing import Dict
from datetime import datetime


def log_path(log_dir: str) -> str:
    return os.path.join(log_dir, f'{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.log')


def logging_config(file_path: str) -> Dict:
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'root': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG'
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'generic',
                'level': 'INFO'
            },
            'file': {
                'class': 'logging.FileHandler',
                'formatter': 'generic',
                'filename': file_path,
                'encoding': 'utf-8',
                'level': 'DEBUG'
            }
        },
        'formatters': {
            'generic': {
                'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
                'class': 'logging.Formatter'
            }
        }
    }

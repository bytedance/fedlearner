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
"""
  This file is used by gunicorn command line at runtime, so it's better away from other dependencies.

  Thus, `environ` is used instead of `envs.Envs`
"""
from os import environ

bind = f':{environ.get("RESTFUL_LISTEN_PORT", 1991)}'
# For some hook which installing some dependencies at runtime, worker timeout should be longer.
timeout = 600
workers = 1
threads = 10
worker_class = 'gthread'
secure_scheme_headers = {'X-FORWARDED-PROTOCOL': 'https', 'X-FORWARDED-PROTO': 'https', 'X-FORWARDED-SSL': 'on'}

errorlog = f'{environ.get("FEDLEARNER_WEBCONSOLE_LOG_DIR}", ".")}/error.log'

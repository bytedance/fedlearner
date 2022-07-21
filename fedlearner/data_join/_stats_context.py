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
import threading
from fedlearner.common import stats

class _StatsContext:
    def __init__(self):
        self.job = os.getenv("FL_JOB") \
                   or os.getenv("APPLICATION_ID") \
                   or "unknown"
        self.uuid = os.getenv("UUID") \
                    or "unknown"
        self.task = os.getenv("FL_TASK") \
                    or "unknown"
        self.task_index = os.getenv("FL_TASK_INDEX") \
                          or os.getenv("INDEX") \
                          or "0"
        self.task_index = int(self.task_index)

        self._stats_client = None

        self._lock = threading.Lock()

    @property
    def stats_client(self):
        if self._stats_client:
            return self._stats_client

        with self._lock:
            if not self._stats_client:
                self._stats_client = stats.with_tags({
                    "job": self.job,
                    "uuid": self.uuid,
                    "task": self.task,
                    "task_index": self.task_index,
                })

        return self._stats_client

stats_context = _StatsContext()

# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
import logging
import threading

from fedlearner_webconsole.composer.interface import IRunner


class RunnerCache(object):
    def __init__(self, runner_fn: dict):
        self._lock = threading.Lock()
        self._cache = {}  # id:name => obj
        self.runner_fn = runner_fn

    def find_runner(self, runner_id: int, runner_name: str) -> IRunner:
        """Find runner

        Args:
             runner_id: id in runner table
             runner_name: {item_type}_{item_id}
        """
        with self._lock:
            key = self.cache_key(runner_id, runner_name)
            obj = self._cache.get(key, None)
            if obj:
                return obj
            item_type, item_id = runner_name.rsplit('_', 1)
            if item_type not in self.runner_fn:
                logging.error(
                    f'failed to find item_type {item_type} in runner_fn, '
                    f'please register it in global_runner_fn')
                raise ValueError(f'unknown item_type {item_type} in runner')
            obj = self.runner_fn[item_type](int(item_id))
            self._cache[key] = obj
            return obj

    def del_runner(self, runner_id: int, runner_name: str):
        """Delete runner

        Args:
             runner_id: id in runner table
             runner_name: {item_type}_{item_id}
        """
        with self._lock:
            key = self.cache_key(runner_id, runner_name)
            del self._cache[key]

    @staticmethod
    def cache_key(runner_id: int, runner_name: str) -> str:
        return f'{runner_id}:{runner_name}'

    @property
    def data(self) -> dict:
        with self._lock:
            return self._cache

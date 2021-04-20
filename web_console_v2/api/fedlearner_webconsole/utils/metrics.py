# Copyright 2021 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import logging
from abc import ABCMeta, abstractmethod


class MetricsHandler(metaclass=ABCMeta):
    @abstractmethod
    def emit_counter(self, name, value: int, tags: dict = None):
        """Emits counter metrics which will be accumulated.

        Args:
            name: name of the metrics, e.g. foo.bar
            value: value of the metrics in integer, e.g. 43
            tags: extra tags of the counter, e.g. {"is_test": True}
        """

    @abstractmethod
    def emit_store(self, name, value: int, tags: dict = None):
        """Emits store metrics.

        Args:
            name: name of the metrics, e.g. foo.bar
            value: value of the metrics in integer, e.g. 43
            tags: extra tags of the counter, e.g. {"is_test": True}
        """


class _DefaultMetricsHandler(MetricsHandler):

    def emit_counter(self, name, value: int, tags: dict = None):
        logging.info(f'[Metric][Counter] {name}: {value}', extra=tags or {})

    def emit_store(self, name, value: int, tags: dict = None):
        logging.info(f'[Metric][Store] {name}: {value}', extra=tags or {})


class _Client(MetricsHandler):
    """A wrapper for all handlers.

    Inspired by logging module, use this to avoid usage of global statement,
    which will make the code more thread-safe."""
    _handlers = []

    def __init__(self):
        self._handlers.append(_DefaultMetricsHandler())

    def emit_counter(self, name, value: int, tags: dict = None):
        for handler in self._handlers:
            handler.emit_counter(name, value, tags)

    def emit_store(self, name, value: int, tags: dict = None):
        for handler in self._handlers:
            handler.emit_store(name, value, tags)

    def add_handler(self, handler):
        self._handlers.append(handler)

    def reset_handlers(self):
        # Only keep the first one
        del self._handlers[1:]


# Exports all to module level
_client = _Client()
emit_counter = _client.emit_counter
emit_store = _client.emit_store
add_handler = _client.add_handler
reset_handlers = _client.reset_handlers

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
import unittest

from fedlearner_webconsole.utils import metrics
from fedlearner_webconsole.utils.metrics import _DefaultMetricsHandler, MetricsHandler


class _FakeMetricsHandler(MetricsHandler):

    def emit_counter(self, name, value: int, tags: dict = None):
        logging.info(f'[Test][Counter] {name} - {value}')

    def emit_store(self, name, value: int, tags: dict = None):
        logging.info(f'[Test][Store] {name} - {value}')


class DefaultMetricsHandler(unittest.TestCase):
    def setUp(self):
        self._handler = _DefaultMetricsHandler()

    def test_emit_counter(self):
        with self.assertLogs() as cm:
            self._handler.emit_counter('test', 1)
            self._handler.emit_counter('test2', 2)
            logs = [r.msg for r in cm.records]
            self.assertEqual(logs, [
                '[Metric][Counter] test: 1',
                '[Metric][Counter] test2: 2'])

    def test_emit_store(self):
        with self.assertLogs() as cm:
            self._handler.emit_store('test', 199)
            self._handler.emit_store('test2', 299)
            logs = [r.msg for r in cm.records]
            self.assertEqual(logs, [
                '[Metric][Store] test: 199',
                '[Metric][Store] test2: 299'])


class ClientTest(unittest.TestCase):
    def setUp(self):
        metrics.add_handler(_FakeMetricsHandler())

    def tearDown(self):
        metrics.reset_handlers()

    def test_emit_counter(self):
        with self.assertLogs() as cm:
            metrics.emit_counter('test', 1)
            logs = [r.msg for r in cm.records]
            self.assertEqual(logs, [
                '[Metric][Counter] test: 1',
                '[Test][Counter] test - 1'])

    def test_emit_store(self):
        with self.assertLogs() as cm:
            metrics.emit_store('test', 199)
            logs = [r.msg for r in cm.records]
            self.assertEqual(logs, [
                '[Metric][Store] test: 199',
                '[Test][Store] test - 199'])


if __name__ == '__main__':
    unittest.main()

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
import json
import logging
import unittest
from io import StringIO
from unittest.mock import patch
from typing import Dict

from opentelemetry import trace as otel_trace, _metrics as otel_metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk._metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

from fedlearner_webconsole.utils import metrics
from fedlearner_webconsole.utils.metrics import _DefaultMetricsHandler, MetricsHandler, OpenTelemetryMetricsHandler


class _FakeMetricsHandler(MetricsHandler):

    def emit_counter(self, name, value: int, tags: Dict[str, str] = None):
        logging.info(f'[Test][Counter] {name} - {value}')

    def emit_store(self, name, value: int, tags: Dict[str, str] = None):
        logging.info(f'[Test][Store] {name} - {value}')


class DefaultMetricsHandler(unittest.TestCase):

    def setUp(self):
        self._handler = _DefaultMetricsHandler()

    def test_emit_counter(self):
        with self.assertLogs() as cm:
            self._handler.emit_counter('test', 1)
            self._handler.emit_counter('test2', 2)
            logs = [r.msg for r in cm.records]
            self.assertEqual(logs, ['[Metric][Counter] test: 1, tags={}', '[Metric][Counter] test2: 2, tags={}'])

    def test_emit_store(self):
        with self.assertLogs() as cm:
            self._handler.emit_store('test', 199)
            self._handler.emit_store('test2', 299)
            logs = [r.msg for r in cm.records]
            self.assertEqual(logs, ['[Metric][Store] test: 199, tags={}', '[Metric][Store] test2: 299, tags={}'])


class ClientTest(unittest.TestCase):

    def setUp(self):
        metrics.add_handler(_FakeMetricsHandler())

    def tearDown(self):
        metrics.reset_handlers()

    def test_emit_counter(self):
        with self.assertRaises(TypeError):
            metrics.emit_counter('test', 1, tags={'name': 1})

        with self.assertLogs() as cm:
            metrics.emit_counter('test', 1)
            logs = [r.msg for r in cm.records]
            self.assertEqual(logs, ['[Metric][Counter] test: 1, tags={}', '[Test][Counter] test - 1'])

    def test_emit_store(self):
        with self.assertRaises(TypeError):
            metrics.emit_store('test', 1, tags={'name': 1})

        with self.assertLogs() as cm:
            metrics.emit_store('test', 199)
            logs = [r.msg for r in cm.records]
            self.assertEqual(logs, ['[Metric][Store] test: 199, tags={}', '[Test][Store] test - 199'])


class OpenTelemetryMetricsHandlerClassMethodTest(unittest.TestCase):

    def setUp(self):
        self._span_out = StringIO()
        self._span_exporter_patcher = patch('fedlearner_webconsole.utils.metrics.OTLPSpanExporter',
                                            lambda **kwargs: ConsoleSpanExporter(out=self._span_out))
        self._metric_out = StringIO()
        self._metric_exporter_patcher = patch('fedlearner_webconsole.utils.metrics.OTLPMetricExporter',
                                              lambda **kwargs: ConsoleMetricExporter(out=self._metric_out))
        self._span_exporter_patcher.start()
        self._metric_exporter_patcher.start()

    def tearDown(self):
        self._metric_exporter_patcher.stop()
        self._span_exporter_patcher.stop()

    def test_new_handler(self):
        OpenTelemetryMetricsHandler.new_handler()
        self.assertEqual(
            otel_trace.get_tracer_provider().resource,
            Resource(
                attributes={
                    'telemetry.sdk.language': 'python',
                    'telemetry.sdk.name': 'opentelemetry',
                    'telemetry.sdk.version': '1.10.0',
                    'service.name': 'fedlearner_webconsole',
                    'deployment.environment': 'default',
                }))
        self.assertEqual(
            otel_metrics.get_meter_provider()._sdk_config.resource,  # pylint: disable=protected-access
            Resource(
                attributes={
                    'telemetry.sdk.language': 'python',
                    'telemetry.sdk.name': 'opentelemetry',
                    'telemetry.sdk.version': '1.10.0',
                    'service.name': 'fedlearner_webconsole',
                    'deployment.environment': 'default',
                }))


class OpenTelemetryMetricsHandlerTest(unittest.TestCase):

    def setUp(self):
        self._span_out = StringIO()
        self._metric_out = StringIO()
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter(out=self._span_out)))
        reader = PeriodicExportingMetricReader(ConsoleMetricExporter(out=self._metric_out),
                                               export_interval_millis=60000)
        meter_provider = MeterProvider(metric_readers=[reader])
        self._tracer_provider = tracer_provider
        self._meter_provider = meter_provider
        self._handler = OpenTelemetryMetricsHandler(tracer=tracer_provider.get_tracer(__file__),
                                                    meter=meter_provider.get_meter(__file__))

    def _force_flush(self):
        self._meter_provider.force_flush()
        self._metric_out.flush()
        self._tracer_provider.force_flush()
        self._span_out.flush()

    def test_emit_store(self):
        # Note that same instrument with different tags won't be aggregated.
        # Aggregation rule for `emit_store` is delivering the last value of this interval.
        # If no value at this interval, no `Metric` will be sent.
        self._handler.emit_store(name='test_store', value=1, tags={'module': 'dataset', 'uuid': 'tag1'})
        self._handler.emit_store(name='test_store', value=5, tags={'module': 'dataset', 'uuid': 'tag2'})
        self._handler.emit_store(name='test_store', value=2, tags={'module': 'dataset', 'uuid': 'tag1'})
        self._force_flush()
        self._force_flush()
        self._force_flush()
        self._handler.emit_store(name='test_store', value=0, tags={'module': 'dataset', 'uuid': 'tag1'})
        self._force_flush()
        self.assertEqual(self._span_out.getvalue(), '')
        self._metric_out.seek(0)
        lines = self._metric_out.readlines()
        measurements = []
        for l in lines:
            measurement = json.loads(l)
            measurements.append(measurement)
        self.assertEqual(len(measurements), 3)
        self.assertEqual(measurements[0]['attributes'], {'uuid': 'tag1', 'module': 'dataset'})
        self.assertEqual(measurements[1]['attributes'], {'uuid': 'tag2', 'module': 'dataset'})
        self.assertEqual(measurements[0]['name'], 'values.test_store')
        self.assertEqual([m['point']['value'] for m in measurements], [2, 5, 0])

    def test_emit_counter(self):
        # Note that same instrument with different tags won't be aggregated.
        # Aggregation rule for `emit_counter` is delivering the accumulated \
        # value with the same tags during this interval.
        # If no value at this interval, a `Metric` with value of last interval will be sent.
        self._handler.emit_counter(name='test_counter', value=1, tags={'module': 'dataset', 'uuid': 'tag1'})
        self._handler.emit_counter(name='test_counter', value=5, tags={'module': 'dataset', 'uuid': 'tag2'})
        self._handler.emit_counter(name='test_counter', value=2, tags={'module': 'dataset', 'uuid': 'tag1'})
        self._force_flush()
        self._force_flush()
        self._handler.emit_counter(name='test_counter', value=-1, tags={'module': 'dataset', 'uuid': 'tag1'})
        self._force_flush()
        self.assertEqual(self._span_out.getvalue(), '')
        self._metric_out.seek(0)
        lines = self._metric_out.readlines()
        measurements = []
        for l in lines:
            measurement = json.loads(l)
            measurements.append(measurement)
        self.assertEqual(len(measurements), 6)
        self.assertEqual(measurements[0]['attributes'], {'uuid': 'tag1', 'module': 'dataset'})
        self.assertEqual(measurements[1]['attributes'], {'uuid': 'tag2', 'module': 'dataset'})
        self.assertEqual(measurement['name'], 'values.test_counter')
        self.assertEqual([m['point']['value'] for m in measurements], [3, 5, 3, 5, 2, 5])


if __name__ == '__main__':
    unittest.main()

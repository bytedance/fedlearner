# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import sys
from typing import Dict, Union
from threading import Lock

from opentelemetry import trace, _metrics as metrics
from opentelemetry._metrics.instrument import UpDownCounter
from opentelemetry._metrics.measurement import Measurement
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk._metrics.export import (PeriodicExportingMetricReader, ConsoleMetricExporter, MetricExporter,
                                               MetricExportResult, Metric, Sequence)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc._metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace.export import (BatchSpanProcessor, ConsoleSpanExporter, SpanExportResult, SpanExporter,
                                            ReadableSpan)

from envs import Envs


def _validate_tags(tags: Dict[str, str]):
    if tags is None:
        return
    for k, v in tags.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise TypeError(f'Expected str, actually {type(k)}: {type(v)}')


class DevNullSpanExporter(SpanExporter):

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


class DevNullMetricExporter(MetricExporter):

    def export(self, metrics: Sequence[Metric]) -> MetricExportResult:  # pylint: disable=redefined-outer-name
        return MetricExportResult.SUCCESS

    def shutdown(self):
        pass


class MetricsHandler(metaclass=ABCMeta):

    @abstractmethod
    def emit_counter(self, name: str, value: Union[int, float], tags: Dict[str, str] = None):
        """Emits counter metrics which will be accumulated.

        Args:
            name: name of the metrics, e.g. foo.bar
            value: value of the metrics in integer, e.g. 43
            tags: extra tags of the counter, e.g. {"is_test": True}
        """

    @abstractmethod
    def emit_store(self, name: str, value: Union[int, float], tags: Dict[str, str] = None):
        """Emits store metrics.

        Args:
            name: name of the metrics, e.g. foo.bar
            value: value of the metrics in integer, e.g. 43
            tags: extra tags of the counter, e.g. {"is_test": True}
        """


class _DefaultMetricsHandler(MetricsHandler):

    def emit_counter(self, name, value: Union[int, float], tags: Dict[str, str] = None):
        tags = tags or {}
        logging.info(f'[Metric][Counter] {name}: {value}, tags={tags}')

    def emit_store(self, name, value: Union[int, float], tags: Dict[str, str] = None):
        tags = tags or {}
        logging.info(f'[Metric][Store] {name}: {value}, tags={tags}')


class OpenTelemetryMetricsHandler(MetricsHandler):

    class Callback:

        def __init__(self) -> None:
            self._measurement_list = []

        def add(self, value: Union[int, float], tags: Dict[str, str]):
            self._measurement_list.append(Measurement(value=value, attributes=tags))

        def __iter__(self):
            return self

        def __next__(self):
            if len(self._measurement_list) == 0:
                raise StopIteration
            return self._measurement_list.pop(0)

        def __call__(self):
            return iter(self)

    @classmethod
    def new_handler(cls) -> 'OpenTelemetryMetricsHandler':
        instrument_module_name = 'fedlearner_webconsole'
        resource = Resource.create(attributes={
            'service.name': instrument_module_name,
            'deployment.environment': Envs.CLUSTER
        })
        # initiailized trace stuff
        if Envs.APM_SERVER_ENDPOINT == 'stdout':
            span_exporter = ConsoleSpanExporter(out=sys.stdout)
        elif Envs.APM_SERVER_ENDPOINT == '/dev/null':
            span_exporter = DevNullSpanExporter()
        else:
            span_exporter = OTLPSpanExporter(endpoint=Envs.APM_SERVER_ENDPOINT)
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(tracer_provider)

        # initiailized meter stuff
        if Envs.APM_SERVER_ENDPOINT == 'stdout':
            metric_exporter = ConsoleMetricExporter(out=sys.stdout)
        elif Envs.APM_SERVER_ENDPOINT == '/dev/null':
            metric_exporter = DevNullMetricExporter()
        else:
            metric_exporter = OTLPMetricExporter(endpoint=Envs.APM_SERVER_ENDPOINT)
        reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=60000)
        meter_provider = MeterProvider(metric_readers=[reader], resource=resource)
        metrics.set_meter_provider(meter_provider=meter_provider)

        return cls(tracer=tracer_provider.get_tracer(instrument_module_name),
                   meter=meter_provider.get_meter(instrument_module_name))

    def __init__(self, tracer: trace.Tracer, meter: metrics.Meter):
        self._tracer = tracer
        self._meter = meter

        self._lock = Lock()
        self._cache: Dict[str, Union[UpDownCounter, OpenTelemetryMetricsHandler.Callback]] = {}

    def emit_counter(self, name: str, value: Union[int, float], tags: Dict[str, str] = None):
        # Note that the `values.` prefix is used for Elastic Index Dynamic Inference.
        # Optimize by decreasing lock.
        if name not in self._cache:
            with self._lock:
                # Double check `self._cache` content.
                if name not in self._cache:
                    counter = self._meter.create_up_down_counter(name=f'values.{name}')
                    self._cache[name] = counter
        assert isinstance(self._cache[name], UpDownCounter)
        self._cache[name].add(value, attributes=tags)

    def emit_store(self, name: str, value: Union[int, float], tags: Dict[str, str] = None):
        # Note that the `values.` prefix is used for Elastic Index Dynamic Inference.
        # Optimize by decreasing lock.
        if name not in self._cache:
            with self._lock:
                # Double check `self._cache` content.
                if name not in self._cache:
                    cb = OpenTelemetryMetricsHandler.Callback()
                    self._meter.create_observable_gauge(name=f'values.{name}', callback=cb)
                    self._cache[name] = cb
        assert isinstance(self._cache[name], OpenTelemetryMetricsHandler.Callback)
        self._cache[name].add(value=value, tags=tags)


class _Client(MetricsHandler):
    """A wrapper for all handlers.

    Inspired by logging module, use this to avoid usage of global statement,
    which will make the code more thread-safe."""
    _handlers = []

    def __init__(self):
        self._handlers.append(_DefaultMetricsHandler())
        # TODO(wangsen.0914): unify this behaviour to py_libs
        self._handlers.append(OpenTelemetryMetricsHandler.new_handler())

    def emit_counter(self, name, value: Union[int, float], tags: Dict[str, str] = None):
        _validate_tags(tags)
        for handler in self._handlers:
            handler.emit_counter(name, value, tags)

    def emit_store(self, name, value: Union[int, float], tags: Dict[str, str] = None):
        _validate_tags(tags)
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

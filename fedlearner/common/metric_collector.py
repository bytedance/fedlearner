# Copyright 2022 The FedLearner Authors. All Rights Reserved.
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
from dataclasses import dataclass
from os import environ
from threading import Lock
from typing import Optional, Union, Dict

from opentelemetry import trace, _metrics as metrics
from opentelemetry._metrics.instrument import UpDownCounter
from opentelemetry._metrics.measurement import Measurement
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk._metrics.export import \
    ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter \
    import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc._metric_exporter \
    import OTLPMetricExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_logger = logging.getLogger(__name__)


@dataclass
class Sample:
    value: Union[int, float]
    labels: Dict[str, str] = None


class MetricCollector:
    _DEFAULT_EXPORT_INTERVAL = 60000

    class Callback:

        def __init__(self) -> None:
            self._measurement_list = []

        def record(self, value: Union[int, float], tags: dict):
            self._measurement_list.append(
                Measurement(value=value, attributes=tags))

        def __iter__(self):
            return self

        def __next__(self):
            if len(self._measurement_list) == 0:
                raise StopIteration
            return self._measurement_list.pop(0)

        def __call__(self):
            return iter(self)

    class EmptyTrace(object):
        def __init__(self):
            pass

        def __enter__(self):
            pass

        def __exit__(self, *a):
            pass

    def __init__(
        self,
        service_name: Optional[str] = None,
        export_interval_millis: Optional[float] = None,
    ):
        enable = environ.get('METRIC_COLLECTOR_ENABLE')
        if enable is None:
            self._ready = False
            return
        elif enable.lower() in ['false', 'f']:
            self._ready = False
            return

        if service_name is None:
            service_name = environ.get('METRIC_COLLECTOR_SERVICE_NAME',
                                       'default_metric_service')
        if export_interval_millis is None:
            try:
                export_interval_millis = float(
                    environ.get('METRIC_COLLECTOR_EXPORT_INTERVAL_MILLIS',
                                self._DEFAULT_EXPORT_INTERVAL)
                )
            except ValueError:
                _logger.info(
                    'Invalid value for export interval, using default %s ms',
                    self._DEFAULT_EXPORT_INTERVAL)
                export_interval_millis = self._DEFAULT_EXPORT_INTERVAL

        # for example, 'http://apm-server-apm-server:8200'
        endpoint = environ.get('METRIC_COLLECTOR_EXPORT_ENDPOINT')
        if endpoint is not None:
            exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
        else:
            exporter = ConsoleMetricExporter()

        reader = PeriodicExportingMetricReader(
            exporter=exporter,
            export_interval_millis=export_interval_millis)
        resource = Resource.create({'service.name': service_name})
        self._meter_provider = MeterProvider(
            metric_readers=[reader],
            resource=resource
        )
        metrics.set_meter_provider(self._meter_provider)
        self._meter = metrics.get_meter_provider().get_meter(service_name)

        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        trace.set_tracer_provider(tracer_provider)
        self._tracer = trace.get_tracer_provider().get_tracer(service_name)

        self._ready = True
        self._lock = Lock()
        self._cache: \
            Dict[str, Union[UpDownCounter, MetricCollector.Callback]] = {}

    def emit_single_point(self,
                          name: str,
                          value: Union[int, float],
                          tags: Dict[str, str] = None):
        if self._ready is False:
            return
        cb = self.Callback()
        self._meter.create_observable_gauge(
            name=f'values.{name}', callback=cb
        )
        cb.record(value=value, tags=tags)

    def emit_timing(self,
                    name: str,
                    tags: Dict[str, str] = None):
        if self._ready is False:
            return self.EmptyTrace()
        return self._tracer.start_as_current_span(name=name, attributes=tags)

    def emit_counter(self,
                     name: str,
                     value: Union[int, float],
                     tags: Dict[str, str] = None):
        if self._ready is False:
            return
        if name not in self._cache:
            with self._lock:
                # Double check `self._cache` content.
                if name not in self._cache:
                    counter = self._meter.create_up_down_counter(
                        name=f'values.{name}'
                    )
                    self._cache[name] = counter
        assert isinstance(self._cache[name], UpDownCounter)
        self._cache[name].add(value, attributes=tags)

    def emit_store(self,
                   name: str,
                   value: Union[int, float],
                   tags: Dict[str, str] = None):
        if self._ready is False:
            return
        if name not in self._cache:
            with self._lock:
                # Double check `self._cache` content.
                if name not in self._cache:
                    cb = self.Callback()
                    self._meter.create_observable_gauge(
                        name=f'values.{name}', callback=cb
                    )
                    self._cache[name] = cb
        assert isinstance(self._cache[name], self.Callback)
        self._cache[name].record(value=value, tags=tags)

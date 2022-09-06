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
from abc import ABC, abstractmethod

from os import environ
from threading import Lock
from typing import Optional, Union, Dict, Iterator

from opentelemetry import trace, _metrics as metrics
from opentelemetry._metrics.instrument import UpDownCounter
from opentelemetry._metrics.measurement import Measurement
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, Span
from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk._metrics.export import \
    ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter \
    import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc._metric_exporter \
    import OTLPMetricExporter
from opentelemetry.sdk.trace.export import \
    BatchSpanProcessor, ConsoleSpanExporter

_logger = logging.getLogger(__name__)


class AbstractCollector(ABC):

    @abstractmethod
    def add_global_tags(self, global_tags: Dict[str, str]):
        pass

    @abstractmethod
    def emit_single_point(self,
                          name: str,
                          value: Union[int, float],
                          tags: Dict[str, str] = None):
        pass

    @abstractmethod
    def emit_timing(self,
                    name: str,
                    tags: Dict[str, str] = None):
        pass

    @abstractmethod
    def emit_counter(self,
                     name: str,
                     value: Union[int, float],
                     tags: Dict[str, str] = None):
        pass

    @abstractmethod
    def emit_store(self,
                   name: str,
                   value: Union[int, float],
                   tags: Dict[str, str] = None):
        pass


class StubCollector(AbstractCollector):

    class EmptyTrace(object):
        def __init__(self):
            pass

        def __enter__(self):
            pass

        def __exit__(self, *a):
            pass

    def add_global_tags(self, global_tags: Dict[str, str]):
        pass

    def emit_single_point(self,
                          name: str,
                          value: Union[int, float],
                          tags: Dict[str, str] = None):
        pass

    def emit_timing(self,
                    name: str,
                    tags: Dict[str, str] = None):
        return self.EmptyTrace()

    def emit_counter(self,
                     name: str,
                     value: Union[int, float],
                     tags: Dict[str, str] = None):
        pass

    def emit_store(self,
                   name: str,
                   value: Union[int, float],
                   tags: Dict[str, str] = None):
        pass


class MetricCollector(AbstractCollector):
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

    def __init__(
        self,
        service_name: Optional[str] = None,
        export_interval_millis: Optional[float] = None,
        custom_service_label: Optional[dict] = None,
    ):
        if service_name is None:
            service_name = environ.get('METRIC_COLLECTOR_SERVICE_NAME',
                                       'default_metric_service')
        cluster_name = environ.get('CLUSTER', 'default_cluster')
        if export_interval_millis is None:
            try:
                export_interval_millis = float(
                    environ.get('METRIC_COLLECTOR_EXPORT_INTERVAL_MILLIS',
                                self._DEFAULT_EXPORT_INTERVAL)
                )
            except ValueError:
                _logger.error(
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
        service_label = {
            'service.name': service_name,
            'deployment.environment': cluster_name
        }
        if custom_service_label is not None:
            service_label.update(custom_service_label)
        resource = Resource.create(service_label)
        self._meter_provider = MeterProvider(
            metric_readers=[reader],
            resource=resource
        )
        metrics.set_meter_provider(self._meter_provider)
        self._meter = metrics.get_meter_provider().get_meter(service_name)

        if endpoint is not None:
            exporter = OTLPSpanExporter(endpoint=endpoint)
        else:
            exporter = ConsoleSpanExporter()
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(exporter)
        )
        trace.set_tracer_provider(tracer_provider)
        self._tracer = trace.get_tracer_provider().get_tracer(service_name)

        self._lock = Lock()
        self._cache: \
            Dict[str, Union[UpDownCounter, MetricCollector.Callback]] = {}

        self._global_tags = {}

    def add_global_tags(self, global_tags: Dict[str, str]):
        self._global_tags.update(global_tags)

    def emit_single_point(self,
                          name: str,
                          value: Union[int, float],
                          tags: Dict[str, str] = None):
        cb = self.Callback()
        self._meter.create_observable_gauge(
            name=f'values.{name}', callback=cb
        )
        cb.record(value=value, tags=self._get_merged_tags(tags))

    def emit_timing(self,
                    name: str,
                    tags: Dict[str, str] = None) -> Iterator[Span]:
        return self._tracer.start_as_current_span(
            name=name, attributes=self._get_merged_tags(tags))

    def emit_counter(self,
                     name: str,
                     value: Union[int, float],
                     tags: Dict[str, str] = None):
        if name not in self._cache:
            with self._lock:
                # Double check `self._cache` content.
                if name not in self._cache:
                    counter = self._meter.create_up_down_counter(
                        name=f'values.{name}'
                    )
                    self._cache[name] = counter
        assert isinstance(self._cache[name], UpDownCounter)
        self._cache[name].add(value, attributes=self._get_merged_tags(tags))

    def emit_store(self,
                   name: str,
                   value: Union[int, float],
                   tags: Dict[str, str] = None):
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
        self._cache[name].record(value=value,
                                 tags=self._get_merged_tags(tags))

    def _get_merged_tags(self, tags: Dict[str, str] = None):
        merged = self._global_tags.copy()
        if tags is not None:
            merged.update(tags)
        return merged


enable = True
enable_env = environ.get('METRIC_COLLECTOR_ENABLE')
if enable_env is None:
    enable = False
elif enable_env.lower() in ['false', 'f']:
    enable = False

k8s_job_name = environ.get('APPLICATION_ID',
                           'default_k8s_job_name')
global_service_label = {'k8s_job_name': k8s_job_name}
metric_collector = MetricCollector(
    custom_service_label=global_service_label) if enable else StubCollector()

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
from os import environ
from typing import Optional, Union, Dict

from opentelemetry import _metrics as metrics
from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk._metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc._metric_exporter \
    import OTLPMetricExporter


_logger = logging.getLogger(__name__)


class MetricCollector:

    _DEFAULT_EXPORT_INTERVAL = 60000

    def __init__(
        self,
        service_name: Optional[str] = None,
        export_interval_millis: Optional[float] = None,
    ):
        # for example, 'http://apm-server-apm-server:8200'
        endpoint = environ.get('METRIC_COLLECTOR_EXPORT_ENDPOINT')
        if endpoint is None:
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
                export_interval_millis = 60000

        exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
        reader = PeriodicExportingMetricReader(
            exporter=exporter,
            export_interval_millis=export_interval_millis
        )
        provider = MeterProvider(
            metric_readers=[reader],
            resource=Resource.create({'service.name': service_name})
        )
        metrics.set_meter_provider(provider)
        self._meter = metrics.get_meter_provider().get_meter(__name__)
        self._ready = True

    def record(self,
               name: str,
               value: Union[int, float],
               labels: Dict[str, str] = None):
        if self._ready is False:
            return
        # counter
        name = 'values.' + name
        up_down_counter = self._meter.create_up_down_counter(name=name)
        up_down_counter.add(value, attributes=labels)

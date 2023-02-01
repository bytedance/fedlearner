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

from py_libs import metrics
from os import environ
from typing import ContextManager, Union, Dict

service_name = environ.get('METRIC_COLLECTOR_SERVICE_NAME', 'default_metric_service')
endpoint = environ.get('METRIC_COLLECTOR_EXPORT_ENDPOINT')

cluster_name = environ.get('CLUSTER', 'default_cluster')
k8s_job_name = environ.get('APPLICATION_ID', 'default_k8s_job_name')
global_service_label = {'k8s_job_name': k8s_job_name}
if endpoint is not None:
    metrics.add_handler(metrics.OpenTelemetryMetricsHandler.new_handler(cluster_name, endpoint, service_name))


def emit_counter(name: str, value: Union[int, float], tags: Dict[str, str] = None):
    metrics.emit_counter(name, value, global_service_label if tags is None else {**tags, **global_service_label})


def emit_timing(name: str, tags: Dict[str, str] = None) -> ContextManager[None]:
    return metrics.emit_timing(name, global_service_label if tags is None else {**tags, **global_service_label})

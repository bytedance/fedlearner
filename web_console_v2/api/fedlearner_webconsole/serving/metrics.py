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

from fedlearner_webconsole.serving.models import ServingModel
from fedlearner_webconsole.utils import metrics


def serving_metrics_emit_counter(name: str, serving_model: ServingModel = None):
    if serving_model is None:
        metrics.emit_counter(name, 1)
        return
    metrics.emit_counter(name,
                         1,
                         tags={
                             'project_id': str(serving_model.project_id),
                             'serving_model_id': str(serving_model.id),
                             'serving_model_name': serving_model.name,
                         })

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

from fedlearner_webconsole.utils.metrics import emit_store
from fedlearner_webconsole.dataset.models import DatasetJobKind, DatasetJobState


def emit_dataset_job_submission_store(uuid: str, kind: DatasetJobKind, coordinator_id: int):
    emit_store(name='dataset.job.submission',
               value=1,
               tags={
                   'uuid': uuid,
                   'kind': kind.name,
                   'coordinator_id': str(coordinator_id),
               })


def emit_dataset_job_duration_store(duration: int, uuid: str, kind: DatasetJobKind, coordinator_id: int,
                                    state: DatasetJobState):
    emit_store(name='dataset.job.duration',
               value=duration,
               tags={
                   'uuid': uuid,
                   'kind': kind.name,
                   'coordinator_id': str(coordinator_id),
                   'state': state.name
               })

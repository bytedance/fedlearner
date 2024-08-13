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

import enum

from sqlalchemy.sql import func
from google.protobuf import text_format

from fedlearner_webconsole.proto.cleanup_pb2 import CleanupPayload, CleanupPb
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobStage
from fedlearner_webconsole.mmgr.models import Model
from fedlearner_webconsole.algorithm.models import Algorithm
from fedlearner_webconsole.utils.pp_datetime import to_timestamp


# Centralized RegistrationIn
class ResourceType(enum.Enum):
    DATASET = Dataset
    DATASET_JOB = DatasetJob
    DATASET_JOB_STAGE = DatasetJobStage
    MODEL = Model
    ALGORITHM = Algorithm
    NO_RESOURCE = None


class CleanupState(enum.Enum):
    WAITING = 'WAITING'
    RUNNING = 'RUNNING'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'
    CANCELED = 'CANCELED'


class Cleanup(db.Model):
    __tablename__ = 'cleanups_v2'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id')
    state = db.Column(db.Enum(CleanupState, native_enum=False, length=64, create_constraint=False),
                      default=CleanupState.WAITING,
                      comment='state')
    target_start_at = db.Column(db.DateTime(timezone=True), comment='target_start_at')
    completed_at = db.Column(db.DateTime(timezone=True), comment='completed_at')
    resource_id = db.Column(db.Integer, comment='resource_id')
    resource_type = db.Column(db.Enum(ResourceType, native_enum=False, length=64, create_constraint=False),
                              comment='resource_type')
    _payload = db.Column(db.Text(), name='payload', comment='the underlying resources that need to be cleaned up')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created_at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           server_onupdate=func.now(),
                           comment='updated_at')

    @property
    def payload(self) -> CleanupPayload:
        if not self._payload:
            return CleanupPayload()
        return text_format.Parse(self._payload, CleanupPayload())

    @payload.setter
    def payload(self, payload: CleanupPayload):
        self._payload = text_format.MessageToString(payload)

    @property
    def is_cancellable(self):
        return self.state in [CleanupState.CANCELED, CleanupState.WAITING]

    def to_proto(self) -> CleanupPb:
        return CleanupPb(id=self.id,
                         state=self.state.name,
                         target_start_at=to_timestamp(self.target_start_at),
                         completed_at=to_timestamp(self.completed_at) if self.completed_at else None,
                         resource_id=self.resource_id,
                         resource_type=self.resource_type.name,
                         payload=self.payload,
                         created_at=to_timestamp(self.created_at),
                         updated_at=to_timestamp(self.updated_at))

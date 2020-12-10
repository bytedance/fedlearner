# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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

import enum

from fedlearner_webconsole.app import db
from fedlearner_webconsole.utils.db_enum import DBEnum
from fedlearner_webconsole.proto import workflow_pb2


class WorkflowState(enum.Enum):
    INVALID = 0

    # 2PC create
    CREATE_COORDINATOR_PREPARE = 1
    CREATE_PARTICIPANT_PREPARE = 2
    CREATE_COORDINATOR_ABORT = 3
    CREATE_PARTICIPANT_ABORT = 4
    CREATE_COORDINATOR_COMMITTABLE = 5
    CREATE_PARTICIPANT_COMMITTABLE = 6
    CREATED = 7

    # 2PC start
    RUNNING_COORDINATOR_PREPARE = 8
    RUNNING_PARTICIPANT_PREPARE = 9
    RUNNING_COORDINATOR_ABORT = 10
    RUNNING_PARTICIPANT_ABORT = 11
    RUNNING_COORDINATOR_COMMITTABLE = 12
    RUNNING_PARTICIPANT_COMMITTABLE = 13
    RUNNING = 14

    # 2PC stop
    # stop cannot be rolled back so participants must vote yes
    STOP_COORDINATOR_PREPARE = 15
    STOP_PARTICIPANT_PREPARE = 16
    STOP_COORDINATOR_ABORT = 17
    STOP_PARTICIPANT_ABORT = 18
    STOP_COORDINATOR_COMMITTABLE = 19
    STOP_PARTICIPANT_COMMITTABLE = 20
    STOPPED = 21


class Workflow(db.Model):
    __tablename__ = 'workflow_v2'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer)
    name = db.Column(db.String(255), index=True)
    config = db.Column(db.Text())
    state = db.Column(DBEnum(WorkflowState), default=WorkflowState.INVALID)

    def set_config(self, proto):
        self.config = proto.SerializeToString()

    def get_config(self):
        proto = workflow_pb2.Workflow()
        proto.ParseFromString(self.config)
        return proto

    def update_state(self, src_state, dst_state):
        if self.state != src_state:
            raise ValueError(
                "Workflow %s failed to transit from %s to %s: "
                "current state is %s"%(
                    self.name, src_state.name,
                    dst_state.name, self.state.name))
        self.state = dst_state

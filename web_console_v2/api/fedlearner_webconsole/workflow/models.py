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
from sqlalchemy.sql import func
from fedlearner_webconsole.db import db, to_dict_mixin
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto import workflow_definition_pb2


class WorkflowStatus(enum.Enum):
    UNSPECIFIED = 0
    CREATE_SENDER_PREPARE = 1
    CREATE_RECEIVER_PREPARE = 2
    CREATE_SENDER_COMMITTABLE = 3
    CREATE_RECEIVER_COMMITTABLE = 4
    CREATED = 5
    FORK_SENDER = 6


@to_dict_mixin(extras={
    'config': (lambda wf: wf.get_config()),
    'peer_config': (lambda wf: wf.get_peer_config()),
    'status': (lambda wf: wf.status.value)
})
class Workflow(db.Model):
    __tablename__ = 'workflow_v2'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), index=True)
    project_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(WorkflowStatus), nullable=False)
    uuid = db.Column(db.String(255), unique=True, nullable=False, index=True)
    forkable = db.Column(db.Boolean, default=False)
    peer_forkable = db.Column(db.Boolean, default=False)
    group_alias = db.Column(db.String(255), index=True)
    config = db.Column(db.Text())
    # TODO: change to config dict to handle muti-participants
    peer_config = db.Column(db.Text())
    comment = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_onupdate=func.now(),
                           server_default=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True))

import enum

from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.db_enum import DBEnum
from fedlearner_webconsole.proto import workflow_pb2


class WorkflowState(enum.Enum):
    INVALID = 0
    NEW = 1
    READY = 2
    RUNNING = 3
    STOPPED = 4


class TransactionState(enum.Enum):
    READY = 0
    ABORTED = 1

    COORDINATOR_PREPARE = 2
    COORDINATOR_COMMITTABLE = 3
    COORDINATOR_COMMITTING = 4
    COORDINATOR_ABORTING = 5

    PARTICIPANT_PREPARE = 6
    PARTICIPANT_COMMITTABLE = 7
    PARTICIPANT_COMMITTING = 8
    PARTICIPANT_ABORTING = 9


class Workflow(db.Model):
    __tablename__ = 'workflow_v2'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer)
    name = db.Column(db.String(255), unique=True, index=True)
    config = db.Column(db.Text())
    state = db.Column(DBEnum(WorkflowState), default=WorkflowState.INVALID)
    target_state = db.Column(DBEnum(WorkflowState), default=WorkflowState.INVALID)
    transaction_state = db.Column(
        DBEnum(TransactionState), default=TransactionState.READY)
    transaction_err = db.Column(db.Text())


    def set_config(self, proto):
        self.config = proto.SerializeToString()

    def get_config(self):
        proto = workflow_definition_pb2.WorkflowDefinition()
        proto.ParseFromString(self.config)
        return proto

    def set_peer_config(self, proto):
        self.peer_config = proto.SerializeToString()

    def get_peer_config(self):
        proto = workflow_definition_pb2.WorkflowDefinition()
        if self.peer_config is not None:
            proto.ParseFromString(self.peer_config)
        return proto

    def get_project_token(self):
        project = Project.query.filter_by(id=self.project_id).first
        return project.token

    def ready(self, config_proto):
        assert self.state == WorkflowState.NEW, \
            "Cannot stop workflow in %s state"%self.state.name
        assert self.target_state == WorkflowState.INVALID and \
            self.transaction_state == TransactionState.READY, \
                "Cannot run workflow: another action is pending"
        self.target_state = WorkflowState.READY
        self.set_config(config_proto)
        # TODO: also create jobs

    def run(self):
        assert self.state == WorkflowState.READY, \
            "Cannot run workflow in %s state"%self.state.name
        assert self.target_state == WorkflowState.INVALID and \
            self.transaction_state == TransactionState.READY, \
                "Cannot run workflow: another action is pending"
        self.target_state = WorkflowState.RUNNING

    def stop(self):
        assert self.state == WorkflowState.RUNNING, \
            "Cannot stop workflow in %s state"%self.state.name
        assert self.target_state == WorkflowState.INVALID and \
            self.transaction_state == TransactionState.READY, \
                "Cannot run workflow: another action is pending"
        self.target_state = WorkflowState.STOPPED

    def reset(self):
        assert self.state == WorkflowState.STOPPED, \
            "Cannot stop workflow in %s state"%self.state.name
        assert self.target_state == WorkflowState.INVALID and \
            self.transaction_state == TransactionState.READY, \
                "Cannot run workflow: another action is pending"
        self.target_state = WorkflowState.READY
        # TODO: also reset jobs

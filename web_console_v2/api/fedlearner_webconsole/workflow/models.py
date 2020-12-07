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
from datetime import datetime
from google.protobuf import json_format
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto import workflow_definition_pb2


class WorkflowStatus(enum.Enum):
    pending_a = 1
    pending = 2
    pending_b = 3
    ready = 4
    deleted = 5
    pending_f = 6
    running = 7
    failed = 8
    complete = 9


class Workflow(db.Model):
    __tablename__ = 'workflow_v2'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, index=True)
    project_token = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum(WorkflowStatus), nullable=False)
    uid = db.Column(db.String(255), unique=True, nullable=False, index=True)
    forkable = db.Column(db.Boolean, default=True)
    group_alias = db.Column(db.String(255), index=True)
    config = db.Column(db.Text())
    peer_config = db.Column(db.Text())
    comment = db.Column(db.String(255))

    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)

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
        proto.ParseFromString(self.peer_config)
        return proto

    def to_dict(self):
        dic = {
            col.name: getattr(self, col.name) for col in self.__table__.columns
        }
        dic['config'] = json_format.MessageToDict(
            self.get_config(), preserving_proto_field_name=True)
        dic['peer_config'] = json_format.MessageToDict(
            self.get_peer_config(), preserving_proto_field_name=True)
        return dic

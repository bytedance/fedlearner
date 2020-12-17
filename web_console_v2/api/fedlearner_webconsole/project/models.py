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

from sqlalchemy.sql import func
from fedlearner_webconsole.db import db, to_dict_mixin
from fedlearner_webconsole.proto import project_pb2


@to_dict_mixin(extras={
    'config': (lambda project: project.get_config())
})
class Project(db.Model):
    __tablename__ = 'projects_v2'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), index=True)
    token = db.Column(db.String(64), index=True)
    config = db.Column(db.Text())
    certificate = db.Column(db.Text())
    comment = db.Column(db.Text())
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_onupdate=func.now(),
                           server_default=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True))

    def set_config(self, proto):
        self.config = proto.SerializeToString()

    def get_config(self):
        proto = project_pb2.Project()
        proto.ParseFromString(self.config)
        return proto

    def set_certificate(self, proto):
        self.certificate = proto.SerializeToString()

    def get_certificate(self):
        proto = project_pb2.Certificate()
        proto.ParseFromString(self.certificate)
        return proto

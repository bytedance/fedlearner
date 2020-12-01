
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

from fedlearner_webconsole.app import db
from fedlearner_webconsole.proto import workflow_pb2

class Workflow(db.Model):
    __tablename__ = 'workflow_v2'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), index=True)
    config = db.Column(db.Text())

    def set_config(self, proto):
        self.config = proto.SerializeToString()

    def get_config(self):
        proto = workflow_pb2.Workflow()
        proto.ParseFromString(self.config)
        return proto
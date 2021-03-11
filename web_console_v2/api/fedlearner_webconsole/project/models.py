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
from sqlalchemy.sql.schema import Index, UniqueConstraint
from fedlearner_webconsole.db import db, to_dict_mixin
from fedlearner_webconsole.proto import project_pb2


@to_dict_mixin(ignores=['certificate'],
               extras={'config': (lambda project: project.get_config())})
class Project(db.Model):
    __tablename__ = 'projects_v2'
    __table_args__ = (UniqueConstraint('name', name='idx_name'),
                      Index('idx_token', 'token'), {
                          'comment': 'webconsole projects',
                          'mysql_engine': 'innodb',
                          'mysql_charset': 'utf8mb4',
                      })
    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   comment='id')
    name = db.Column(db.String(255), comment='name')
    token = db.Column(db.String(64), comment='token')
    config = db.Column(db.LargeBinary(), comment='config')
    certificate = db.Column(db.LargeBinary(), comment='certificate')
    comment = db.Column('cmt', db.Text(), key='comment', comment='comment')
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           comment='created at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           onupdate=func.now(),
                           server_default=func.now(),
                           comment='updated at')
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted at')

    def set_config(self, proto):
        self.config = proto.SerializeToString()

    def get_config(self):
        if self.config is None:
            return None
        proto = project_pb2.Project()
        proto.ParseFromString(self.config)
        return proto

    def set_certificate(self, proto):
        self.certificate = proto.SerializeToString()

    def get_certificate(self):
        if self.certificate is None:
            return None
        proto = project_pb2.CertificateStorage()
        proto.ParseFromString(self.certificate)
        return proto

    def get_namespace(self):
        config = self.get_config()
        if config is not None:
            variables = self.get_config().variables
            for variable in variables:
                if variable.name == 'NAMESPACE':
                    return variable.value
        return 'default'

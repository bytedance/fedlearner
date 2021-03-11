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
from sqlalchemy.sql.schema import Index, UniqueConstraint
from fedlearner_webconsole.db import db, to_dict_mixin
from fedlearner_webconsole.proto import workflow_definition_pb2


@to_dict_mixin(extras={'config': (lambda wft: wft.get_config())})
class WorkflowTemplate(db.Model):
    __tablename__ = 'template_v2'
    __table_args__ = (UniqueConstraint('name', name='uniq_name'),
                      Index('idx_group_alias', 'group_alias'), {
                          'comment': 'workflow template',
                          'mysql_engine': 'innodb',
                          'mysql_charset': 'utf8mb4',
                      })
    id = db.Column(db.Integer, primary_key=True, comment='id')
    name = db.Column(db.String(255), comment='name')
    comment = db.Column('cmt',
                        db.String(255),
                        key='comment',
                        comment='comment')
    group_alias = db.Column(db.String(255),
                            nullable=False,
                            comment='group_alias')
    config = db.Column(db.LargeBinary(), nullable=False, comment='config')
    is_left = db.Column(db.Boolean, comment='is_left')

    def set_config(self, proto):
        self.config = proto.SerializeToString()

    def get_config(self):
        proto = workflow_definition_pb2.WorkflowDefinition()
        proto.ParseFromString(self.config)
        return proto

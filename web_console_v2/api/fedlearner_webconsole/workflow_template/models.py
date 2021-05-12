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

from sqlalchemy.sql.schema import Index, UniqueConstraint
from fedlearner_webconsole.db import db, to_dict_mixin, default_table_args
from fedlearner_webconsole.proto import workflow_definition_pb2


class WorkflowTemplateKind(enum.Enum):
    DEFAULT = 0
    PRESET_DATAJOIN = 1


@to_dict_mixin(
    extras={
        'config': (lambda wt: wt.get_config()),
        'editor_info': (lambda wt: wt.get_editor_info())
    })
class WorkflowTemplate(db.Model):
    __tablename__ = 'template_v2'
    __table_args__ = (UniqueConstraint('name', name='uniq_name'),
                      Index('idx_group_alias', 'group_alias'),
                      default_table_args('workflow template'))
    id = db.Column(db.Integer, primary_key=True, comment='id')
    name = db.Column(db.String(255), comment='name')
    comment = db.Column('cmt',
                        db.String(255),
                        key='comment',
                        comment='comment')
    group_alias = db.Column(db.String(255),
                            nullable=False,
                            comment='group_alias')
    # max store 16777215 bytes (16 MB)
    config = db.Column(db.LargeBinary(16777215),
                       nullable=False,
                       comment='config')
    is_left = db.Column(db.Boolean, comment='is_left')
    editor_info = db.Column(db.LargeBinary(16777215),
                            comment='editor_info',
                            default=b'')
    kind = db.Column(db.Integer,
                     comment='template kind')  # WorkflowTemplateKind enum

    def set_config(self, proto):
        self.config = proto.SerializeToString()

    def set_editor_info(self, proto):
        self.editor_info = proto.SerializeToString()

    def get_config(self):
        proto = workflow_definition_pb2.WorkflowDefinition()
        proto.ParseFromString(self.config)
        return proto

    def get_editor_info(self):
        proto = workflow_definition_pb2.WorkflowTemplateEditorInfo()
        if self.editor_info is not None:
            proto.ParseFromString(self.editor_info)
        return proto

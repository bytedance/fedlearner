# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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

from sqlalchemy import func
from sqlalchemy.orm import deferred
from sqlalchemy.sql.schema import Index, UniqueConstraint

from fedlearner_webconsole.proto.workflow_template_pb2 import WorkflowTemplateRevisionRef, \
    WorkflowTemplateRevisionPb, WorkflowTemplateRef, WorkflowTemplatePb
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.mixins import to_dict_mixin
from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.proto import workflow_definition_pb2
from fedlearner_webconsole.workflow.utils import is_local


class WorkflowTemplateKind(enum.Enum):
    DEFAULT = 0
    PRESET = 1
    PEER = 2


@to_dict_mixin(
    extras={
        'is_local': (lambda wt: wt.is_local()),
        'config': (lambda wt: wt.get_config()),
        'editor_info': (lambda wt: wt.get_editor_info())
    })
class WorkflowTemplate(db.Model):
    __tablename__ = 'template_v2'
    __table_args__ = (UniqueConstraint('name',
                                       name='uniq_name'), Index('idx_group_alias',
                                                                'group_alias'), default_table_args('workflow template'))
    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)
    name = db.Column(db.String(255), comment='name', default='')
    comment = db.Column('cmt', db.String(255), key='comment', comment='comment')
    group_alias = db.Column(db.String(255), nullable=False, comment='group_alias')
    # max store 16777215 bytes (16 MB)
    config = deferred(db.Column(db.LargeBinary(16777215), nullable=False, comment='config'))
    editor_info = deferred(db.Column(db.LargeBinary(16777215), comment='editor_info', default=b''))
    kind = db.Column(db.Integer, comment='template kind', default=0)  # WorkflowTemplateKind enum
    creator_username = db.Column(db.String(255), comment='the username of the creator')
    coordinator_pure_domain_name = db.Column(db.String(255), comment='name of the coordinator')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created_at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           onupdate=func.now(),
                           server_default=func.now(),
                           comment='update_at')
    template_revisions = db.relationship(
        'WorkflowTemplateRevision', primaryjoin='WorkflowTemplate.id == foreign(WorkflowTemplateRevision.template_id)')

    def set_config(self, proto: workflow_definition_pb2.WorkflowDefinition):
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

    def is_local(self):
        job_defs = self.get_config().job_definitions
        for job_def in job_defs:
            if job_def.is_federated:
                return False
        return True

    def to_ref(self) -> WorkflowTemplateRef:
        return WorkflowTemplateRef(id=self.id,
                                   name=self.name,
                                   comment=self.comment,
                                   group_alias=self.group_alias,
                                   kind=self.kind,
                                   coordinator_pure_domain_name=self.coordinator_pure_domain_name)

    def to_proto(self) -> WorkflowTemplateRevisionPb:
        return WorkflowTemplatePb(id=self.id,
                                  comment=self.comment,
                                  created_at=to_timestamp(self.created_at),
                                  config=self.get_config(),
                                  editor_info=self.get_editor_info(),
                                  is_local=is_local(self.get_config()),
                                  name=self.name,
                                  group_alias=self.group_alias,
                                  kind=self.kind,
                                  creator_username=self.creator_username,
                                  updated_at=to_timestamp(self.updated_at),
                                  coordinator_pure_domain_name=self.coordinator_pure_domain_name)


class WorkflowTemplateRevision(db.Model):
    __tablename__ = 'template_revisions_v2'
    __table_args__ = (Index('idx_template_id', 'template_id'),
                      UniqueConstraint('template_id', 'revision_index', name='uniq_revision_index_in_template'),
                      default_table_args('workflow template revision'))
    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)
    revision_index = db.Column(db.Integer, comment='index for the same template')
    comment = db.Column('cmt', db.String(255), key='comment', comment='comment')
    # max store 16777215 bytes (16 MB)
    config = deferred(db.Column(db.LargeBinary(16777215), nullable=False, comment='config'))
    editor_info = deferred(db.Column(db.LargeBinary(16777215), comment='editor_info', default=b''))
    template_id = db.Column(db.Integer, comment='template_id')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created_at')
    template = db.relationship(
        'WorkflowTemplate',
        primaryjoin='WorkflowTemplate.id == foreign(WorkflowTemplateRevision.template_id)',
        # To disable the warning of back_populates
        overlaps='template_revisions')

    def set_config(self, proto: workflow_definition_pb2.WorkflowDefinition):
        self.config = proto.SerializeToString()

    def get_config(self) -> workflow_definition_pb2.WorkflowDefinition:
        proto = workflow_definition_pb2.WorkflowDefinition()
        proto.ParseFromString(self.config)
        return proto

    def get_editor_info(self) -> workflow_definition_pb2.WorkflowTemplateEditorInfo:
        proto = workflow_definition_pb2.WorkflowTemplateEditorInfo()
        if self.editor_info is not None:
            proto.ParseFromString(self.editor_info)
        return proto

    def to_ref(self) -> WorkflowTemplateRevisionRef:
        return WorkflowTemplateRevisionRef(id=self.id,
                                           revision_index=self.revision_index,
                                           comment=self.comment,
                                           template_id=self.template_id,
                                           created_at=to_timestamp(self.created_at))

    def to_proto(self) -> WorkflowTemplateRevisionPb:
        return WorkflowTemplateRevisionPb(id=self.id,
                                          revision_index=self.revision_index,
                                          comment=self.comment,
                                          template_id=self.template_id,
                                          created_at=to_timestamp(self.created_at),
                                          config=self.get_config(),
                                          editor_info=self.get_editor_info(),
                                          is_local=is_local(self.get_config()),
                                          name=self.template and self.template.name)

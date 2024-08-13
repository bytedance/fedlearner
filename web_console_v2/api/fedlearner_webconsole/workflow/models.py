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
# pylint: disable=use-a-generator
import enum
from typing import List, Optional

from sqlalchemy.orm import deferred
from sqlalchemy.sql import func
from sqlalchemy import UniqueConstraint

from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.proto.workflow_pb2 import WorkflowRef, WorkflowPb
from fedlearner_webconsole.utils.mixins import to_dict_mixin
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto import (common_pb2, workflow_definition_pb2)
from fedlearner_webconsole.job.models import JobState, Job
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.workflow.utils import is_local
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate, WorkflowTemplateRevision


class WorkflowState(enum.Enum):
    INVALID = 0
    NEW = 1
    READY = 2
    RUNNING = 3
    STOPPED = 4
    COMPLETED = 5
    FAILED = 6


class WorkflowExternalState(enum.Enum):
    # state of workflow is unknown
    UNKNOWN = 0
    # workflow is completed
    COMPLETED = 1
    # workflow is failed
    FAILED = 2
    # workflow is stopped
    STOPPED = 3
    # workflow is running
    RUNNING = 4
    # workflow is prepare to run
    PREPARE_RUN = 5
    # workflow is prepare to stop
    PREPARE_STOP = 6
    # workflow is warming up under the hood
    WARMUP_UNDERHOOD = 7
    # workflow is pending participant accept
    PENDING_ACCEPT = 8
    # workflow is ready to run
    READY_TO_RUN = 9
    # workflow is waiting for participant configure
    PARTICIPANT_CONFIGURING = 10
    # workflow is invalid
    INVALID = 11


# yapf: disable
VALID_TRANSITIONS = [
    (WorkflowState.NEW, WorkflowState.READY),
    (WorkflowState.READY, WorkflowState.RUNNING),
    (WorkflowState.READY, WorkflowState.STOPPED),

    (WorkflowState.RUNNING, WorkflowState.STOPPED),
    # Transitions below are not used, because state controller treat COMPLETED and FAILED as STOPPED.
    # (WorkflowState.RUNNING, WorkflowState.COMPLETED),
    # (WorkflowState.RUNNING, WorkflowState.FAILED),


    (WorkflowState.STOPPED, WorkflowState.RUNNING),
    (WorkflowState.COMPLETED, WorkflowState.RUNNING),
    (WorkflowState.FAILED, WorkflowState.RUNNING),
    (WorkflowState.RUNNING, WorkflowState.RUNNING),

    # This is hack to make workflow_state_controller's committing stage idempotent.
    (WorkflowState.STOPPED, WorkflowState.STOPPED),
    (WorkflowState.COMPLETED, WorkflowState.STOPPED),
    (WorkflowState.FAILED, WorkflowState.STOPPED)
]
# yapf: enable


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


VALID_TRANSACTION_TRANSITIONS = [
    (TransactionState.ABORTED, TransactionState.READY),
    (TransactionState.READY, TransactionState.PARTICIPANT_ABORTING),
    (TransactionState.READY, TransactionState.COORDINATOR_PREPARE),
    # (TransactionState.COORDINATOR_PREPARE,
    #  TransactionState.COORDINATOR_COMMITTABLE),
    (TransactionState.COORDINATOR_COMMITTABLE, TransactionState.COORDINATOR_COMMITTING),
    # (TransactionState.COORDINATOR_PREPARE,
    #  TransactionState.COORDINATOR_ABORTING),
    (TransactionState.COORDINATOR_COMMITTABLE, TransactionState.COORDINATOR_ABORTING),
    (TransactionState.COORDINATOR_ABORTING, TransactionState.ABORTED),
    (TransactionState.READY, TransactionState.PARTICIPANT_PREPARE),
    # (TransactionState.PARTICIPANT_PREPARE,
    #  TransactionState.PARTICIPANT_COMMITTABLE),
    (TransactionState.PARTICIPANT_COMMITTABLE, TransactionState.PARTICIPANT_COMMITTING),
    # (TransactionState.PARTICIPANT_PREPARE,
    #  TransactionState.PARTICIPANT_ABORTING),
    (TransactionState.PARTICIPANT_COMMITTABLE, TransactionState.PARTICIPANT_ABORTING),
    # (TransactionState.PARTICIPANT_ABORTING,
    #  TransactionState.ABORTED),
]

IGNORED_TRANSACTION_TRANSITIONS = [
    (TransactionState.PARTICIPANT_COMMITTABLE, TransactionState.PARTICIPANT_PREPARE),
]


def compare_yaml_templates_in_wf(wf_a: workflow_definition_pb2.WorkflowDefinition,
                                 wf_b: workflow_definition_pb2.WorkflowDefinition):
    """"Compare two WorkflowDefinition's each template,
     return True if any job different"""
    if len(wf_a.job_definitions) != len(wf_b.job_definitions):
        return False
    job_defs_a = wf_a.job_definitions
    job_defs_b = wf_b.job_definitions
    return any([
        job_defs_a[i].yaml_template != job_defs_b[i].yaml_template or job_defs_a[i].name != job_defs_b[i].name
        for i in range(len(job_defs_a))
    ])


@to_dict_mixin(ignores=['fork_proposal_config', 'config', 'editor_info'],
               extras={
                   'job_ids': (lambda wf: wf.get_job_ids()),
                   'create_job_flags': (lambda wf: wf.get_create_job_flags()),
                   'peer_create_job_flags': (lambda wf: wf.get_peer_create_job_flags()),
                   'state': (lambda wf: wf.get_state_for_frontend()),
                   'is_local': (lambda wf: wf.is_local())
               })
class Workflow(db.Model):
    __tablename__ = 'workflow_v2'
    __table_args__ = (UniqueConstraint('uuid', name='uniq_uuid'),
                      UniqueConstraint('project_id', 'name', name='uniq_name_in_project'), {
                          'comment': 'workflow_v2',
                          'mysql_engine': 'innodb',
                          'mysql_charset': 'utf8mb4',
                      })
    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)
    uuid = db.Column(db.String(64), comment='uuid')
    name = db.Column(db.String(255), comment='name')
    project_id = db.Column(db.Integer, comment='project_id')
    template_id = db.Column(db.Integer, comment='template_id', nullable=True)
    template_revision_id = db.Column(db.Integer, comment='template_revision_id', nullable=True)
    editor_info = deferred(db.Column(db.LargeBinary(16777215), comment='editor_info', default=b'', nullable=True))
    # max store 16777215 bytes (16 MB)
    config = deferred(db.Column(db.LargeBinary(16777215), comment='config'))
    comment = db.Column('cmt', db.String(255), key='comment', comment='comment')

    metric_is_public = db.Column(db.Boolean(), default=False, nullable=False, comment='metric_is_public')
    create_job_flags = db.Column(db.TEXT(), comment='create_job_flags')

    job_ids = db.Column(db.TEXT(), comment='job_ids')

    forkable = db.Column(db.Boolean, default=False, comment='forkable')
    forked_from = db.Column(db.Integer, default=None, comment='forked_from')
    # index in config.job_defs instead of job's id
    peer_create_job_flags = db.Column(db.TEXT(), comment='peer_create_job_flags')
    # max store 16777215 bytes (16 MB)
    fork_proposal_config = db.Column(db.LargeBinary(16777215), comment='fork_proposal_config')
    trigger_dataset = db.Column(db.Integer, comment='trigger_dataset')
    last_triggered_batch = db.Column(db.Integer, comment='last_triggered_batch')

    state = db.Column(db.Enum(WorkflowState, native_enum=False, create_constraint=False, name='workflow_state'),
                      default=WorkflowState.INVALID,
                      comment='state')
    target_state = db.Column(db.Enum(WorkflowState,
                                     native_enum=False,
                                     create_constraint=False,
                                     name='workflow_target_state'),
                             default=WorkflowState.INVALID,
                             comment='target_state')
    transaction_state = db.Column(db.Enum(TransactionState, native_enum=False, create_constraint=False),
                                  default=TransactionState.READY,
                                  comment='transaction_state')
    transaction_err = db.Column(db.Text(), comment='transaction_err')

    start_at = db.Column(db.Integer, comment='start_at')
    stop_at = db.Column(db.Integer, comment='stop_at')

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created_at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           onupdate=func.now(),
                           server_default=func.now(),
                           comment='update_at')

    extra = db.Column(db.Text(), comment='json string that will be send to peer')  # deprecated
    local_extra = db.Column(db.Text(), comment='json string that will only be store locally')  # deprecated
    cron_config = db.Column('cronjob_config', db.Text(), key='cron_config', comment='cronjob json string')

    creator = db.Column(db.String(255), comment='the username of the creator')
    favour = db.Column(db.Boolean, default=False, comment='favour')

    owned_jobs = db.relationship(
        'Job',
        primaryjoin='foreign(Job.workflow_id) == Workflow.id',
        # To disable the warning of back_populates
        overlaps='workflow')
    project = db.relationship(Project.__name__, primaryjoin='Project.id == foreign(Workflow.project_id)')
    template = db.relationship(WorkflowTemplate.__name__,
                               primaryjoin='WorkflowTemplate.id == foreign(Workflow.template_id)')
    template_revision = db.relationship(
        WorkflowTemplateRevision.__name__,
        primaryjoin='WorkflowTemplateRevision.id == foreign(Workflow.template_revision_id)',
        # To disable the warning of back_populates
        overlaps='workflows')

    def is_finished(self) -> bool:
        return all([job.is_disabled or job.state == JobState.COMPLETED for job in self.owned_jobs])

    def is_failed(self) -> bool:
        return any([job.state == JobState.FAILED for job in self.owned_jobs])

    def get_state_for_frontend(self) -> WorkflowExternalState:
        """Get workflow states that frontend need."""

        # states in workflow creating stage.
        if self.state == WorkflowState.NEW \
                and self.target_state == WorkflowState.READY:
            if self.transaction_state in [
                    TransactionState.PARTICIPANT_COMMITTABLE, TransactionState.PARTICIPANT_COMMITTING,
                    TransactionState.COORDINATOR_COMMITTING
            ]:
                return WorkflowExternalState.WARMUP_UNDERHOOD
            if self.transaction_state == TransactionState.PARTICIPANT_PREPARE:
                return WorkflowExternalState.PENDING_ACCEPT
            if self.transaction_state in [
                    TransactionState.READY, TransactionState.COORDINATOR_COMMITTABLE,
                    TransactionState.COORDINATOR_PREPARE
            ]:
                return WorkflowExternalState.PARTICIPANT_CONFIGURING

        # static state
        if self.state == WorkflowState.READY:
            return WorkflowExternalState.READY_TO_RUN

        if self.state == WorkflowState.RUNNING:
            return WorkflowExternalState.RUNNING

        if self.state == WorkflowState.STOPPED:
            return WorkflowExternalState.STOPPED
        if self.state == WorkflowState.COMPLETED:
            return WorkflowExternalState.COMPLETED
        if self.state == WorkflowState.FAILED:
            return WorkflowExternalState.FAILED

        if self.state == WorkflowState.INVALID:
            return WorkflowExternalState.INVALID

        return WorkflowExternalState.UNKNOWN

    def set_config(self, proto: WorkflowDefinition):
        if proto is not None:
            self.config = proto.SerializeToString()
        else:
            self.config = None

    def get_config(self) -> Optional[WorkflowDefinition]:
        if self.config is not None:
            proto = WorkflowDefinition()
            proto.ParseFromString(self.config)
            return proto
        return None

    def set_fork_proposal_config(self, proto):
        if proto is not None:
            self.fork_proposal_config = proto.SerializeToString()
        else:
            self.fork_proposal_config = None

    def get_fork_proposal_config(self):
        if self.fork_proposal_config is not None:
            proto = workflow_definition_pb2.WorkflowDefinition()
            proto.ParseFromString(self.fork_proposal_config)
            return proto
        return None

    def set_job_ids(self, job_ids):
        self.job_ids = ','.join([str(i) for i in job_ids])

    def get_job_ids(self):
        if not self.job_ids:
            return []
        return [int(i) for i in self.job_ids.split(',')]

    def get_jobs(self, session) -> List[Job]:
        job_ids = self.get_job_ids()
        return session.query(Job).filter(Job.id.in_(job_ids)).all()

    def set_create_job_flags(self, create_job_flags):
        if not create_job_flags:
            self.create_job_flags = None
        else:
            flags = []
            for i in create_job_flags:
                assert isinstance(i, int)
                flags.append(str(i))
            self.create_job_flags = ','.join(flags)

    def get_create_job_flags(self):
        if self.create_job_flags is None:
            config = self.get_config()
            if config is None:
                return None
            num_jobs = len(config.job_definitions)
            return [common_pb2.CreateJobFlag.NEW] * num_jobs
        return [int(i) for i in self.create_job_flags.split(',')]

    def set_peer_create_job_flags(self, peer_create_job_flags):
        if not peer_create_job_flags:
            self.peer_create_job_flags = None
        else:
            flags = []
            for i in peer_create_job_flags:
                assert isinstance(i, int)
                flags.append(str(i))
            self.peer_create_job_flags = ','.join(flags)

    def get_peer_create_job_flags(self):
        if self.peer_create_job_flags is None:
            return None
        return [int(i) for i in self.peer_create_job_flags.split(',')]

    def to_workflow_ref(self) -> WorkflowRef:
        return WorkflowRef(id=self.id,
                           name=self.name,
                           uuid=self.uuid,
                           project_id=self.project_id,
                           state=self.get_state_for_frontend().name,
                           created_at=to_timestamp(self.created_at),
                           forkable=self.forkable,
                           metric_is_public=self.metric_is_public,
                           favour=self.favour)

    def to_proto(self) -> WorkflowPb:
        return WorkflowPb(id=self.id,
                          name=self.name,
                          uuid=self.uuid,
                          project_id=self.project_id,
                          state=self.get_state_for_frontend().name,
                          created_at=to_timestamp(self.created_at),
                          forkable=self.forkable,
                          metric_is_public=self.metric_is_public,
                          favour=self.favour,
                          template_revision_id=self.template_revision_id,
                          template_id=self.template_id,
                          config=self.get_config(),
                          editor_info=self.get_editor_info(),
                          comment=self.comment,
                          job_ids=self.get_job_ids(),
                          create_job_flags=self.get_create_job_flags(),
                          is_local=self.is_local(),
                          forked_from=self.forked_from,
                          peer_create_job_flags=self.get_peer_create_job_flags(),
                          start_at=self.start_at,
                          stop_at=self.stop_at,
                          updated_at=to_timestamp(self.updated_at),
                          cron_config=self.cron_config,
                          creator=self.creator,
                          template_info=self.get_template_info())

    def is_local(self):
        return is_local(self.get_config(), self.get_create_job_flags())

    def get_template_info(self) -> WorkflowPb.TemplateInfo:
        template_info = WorkflowPb.TemplateInfo(id=self.template_id, is_modified=True)
        if self.template is not None:
            template_info.name = self.template.name
            template_info.is_modified = compare_yaml_templates_in_wf(self.get_config(), self.template.get_config())

        if self.template_revision is not None:
            template_info.is_modified = False
            template_info.revision_index = self.template_revision.revision_index
        return template_info

    def get_editor_info(self):
        proto = workflow_definition_pb2.WorkflowTemplateEditorInfo()
        if self.editor_info is not None:
            proto.ParseFromString(self.editor_info)
        return proto

    def is_invalid(self):
        return self.state == WorkflowState.INVALID

    def can_transit_to(self, target_state: WorkflowState):
        return (self.state, target_state) in VALID_TRANSITIONS

    def update_target_state(self, target_state):
        if self.target_state not in [target_state, WorkflowState.INVALID]:
            raise ValueError(f'Another transaction is in progress ' f'[{self.id}]')
        if target_state != WorkflowState.READY:
            raise ValueError(f'Invalid target_state ' f'{self.target_state}')
        if (self.state, target_state) not in VALID_TRANSITIONS:
            raise ValueError(f'Invalid transition from ' f'{self.state} to {target_state}')

        self.target_state = target_state

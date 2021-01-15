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
# pylint: disable=broad-except

import logging
import enum

from sqlalchemy.sql import func
from fedlearner_webconsole.db import db, to_dict_mixin
from fedlearner_webconsole.proto import workflow_definition_pb2
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.job.models import Job, JobState, JobType
from fedlearner_webconsole.scheduler.job_scheduler import job_scheduler
class WorkflowState(enum.Enum):
    INVALID = 0
    NEW = 1
    READY = 2
    RUNNING = 3
    STOPPED = 4


VALID_TRANSITIONS = [(WorkflowState.NEW, WorkflowState.READY),
                     (WorkflowState.READY, WorkflowState.RUNNING),
                     (WorkflowState.RUNNING, WorkflowState.STOPPED),
                     (WorkflowState.STOPPED, WorkflowState.RUNNING)]


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
    (TransactionState.COORDINATOR_COMMITTABLE,
     TransactionState.COORDINATOR_COMMITTING),
    # (TransactionState.COORDINATOR_PREPARE,
    #  TransactionState.COORDINATOR_ABORTING),
    (TransactionState.COORDINATOR_COMMITTABLE,
     TransactionState.COORDINATOR_ABORTING),
    (TransactionState.COORDINATOR_ABORTING, TransactionState.ABORTED),
    (TransactionState.READY, TransactionState.PARTICIPANT_PREPARE),
    # (TransactionState.PARTICIPANT_PREPARE,
    #  TransactionState.PARTICIPANT_COMMITTABLE),
    (TransactionState.PARTICIPANT_COMMITTABLE,
     TransactionState.PARTICIPANT_COMMITTING),
    # (TransactionState.PARTICIPANT_PREPARE,
    #  TransactionState.PARTICIPANT_ABORTING),
    (TransactionState.PARTICIPANT_COMMITTABLE,
     TransactionState.PARTICIPANT_ABORTING),
    # (TransactionState.PARTICIPANT_ABORTING,
    #  TransactionState.ABORTED),
]

IGNORED_TRANSACTION_TRANSITIONS = [
    (TransactionState.PARTICIPANT_COMMITTABLE,
     TransactionState.PARTICIPANT_PREPARE),
]


@to_dict_mixin(ignores=['forked_from'],
               extras={
                   'config': (lambda wf: wf.get_config()),
               })
class Workflow(db.Model):
    __tablename__ = 'workflow_v2'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey(Project.id))
    config = db.Column(db.Text())
    forkable = db.Column(db.Boolean, default=False)
    forked_from = db.Column(db.Integer, default=None)
    comment = db.Column(db.String(255))

    state = db.Column(db.Enum(WorkflowState), default=WorkflowState.INVALID)
    target_state = db.Column(db.Enum(WorkflowState),
                             default=WorkflowState.INVALID)
    transaction_state = db.Column(db.Enum(TransactionState),
                                  default=TransactionState.READY)
    transaction_err = db.Column(db.Text())
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_onupdate=func.now(),
                           server_default=func.now())
    jobs = db.relationship('Job', back_populates='workflow')
    project = db.relationship(Project)

    def set_config(self, proto):
        if proto is not None:
            self.config = proto.SerializeToString()
        else:
            self.config = None

    def get_config(self):
        if self.config is not None:
            proto = workflow_definition_pb2.WorkflowDefinition()
            proto.ParseFromString(self.config)
            return proto
        return None

    def update_target_state(self, target_state):
        if self.target_state != target_state \
                and self.target_state != WorkflowState.INVALID:
            raise ValueError(f'Another transaction is in progress [{self.id}]')
        if target_state not in [WorkflowState.READY,
                                WorkflowState.RUNNING,
                                WorkflowState.STOPPED]:
            raise ValueError(
                f'Invalid target_state {self.target_state}')
        if (self.state, target_state) not in VALID_TRANSITIONS:
            raise ValueError(
                f'Invalid transition from {self.state} to {target_state}')
        self.target_state = target_state

    def update_state(self, asserted_state, target_state, transaction_state):
        assert asserted_state is None or self.state == asserted_state, \
            'Cannot change current state directly'

        if transaction_state != self.transaction_state:
            if (self.transaction_state, transaction_state) in \
                    IGNORED_TRANSACTION_TRANSITIONS:
                return self.transaction_state
            assert (self.transaction_state, transaction_state) in \
                   VALID_TRANSACTION_TRANSITIONS, \
                'Invalid transaction transition from {} to {}'.format(
                    self.transaction_state, transaction_state)
            self.transaction_state = transaction_state

        # coordinator prepare & rollback
        if self.transaction_state == TransactionState.COORDINATOR_PREPARE:
            self.prepare(target_state)
        if self.transaction_state == TransactionState.COORDINATOR_ABORTING:
            self.rollback()

        # participant prepare & rollback & commit
        if self.transaction_state == TransactionState.PARTICIPANT_PREPARE:
            self.prepare(target_state)
        if self.transaction_state == TransactionState.PARTICIPANT_ABORTING:
            self.rollback()
            self.transaction_state = TransactionState.ABORTED
        if self.transaction_state == TransactionState.PARTICIPANT_COMMITTING:
            self.commit()

        return self.transaction_state

    def prepare(self, target_state):
        assert self.transaction_state in [
            TransactionState.COORDINATOR_PREPARE,
            TransactionState.PARTICIPANT_PREPARE], \
            'Workflow not in prepare state'

        # TODO(tjulinfan): remove this
        if target_state is None:
            # No action
            return

        # Validation
        try:
            self.update_target_state(target_state)
        except ValueError as e:
            logging.warning(
                'Error during update target state in prepare: %s', str(e))
            self.transaction_state = TransactionState.ABORTED
            return

        success = True
        if self.target_state == WorkflowState.READY:
            # This is a hack, if config is not set then
            # no action needed
            # TODO(tjulinfan): validate if the config is legal or not
            success = bool(self.config)
        if success:
            if self.transaction_state == TransactionState.COORDINATOR_PREPARE:
                self.transaction_state = \
                    TransactionState.COORDINATOR_COMMITTABLE
            else:
                self.transaction_state = \
                    TransactionState.PARTICIPANT_COMMITTABLE


    def rollback(self):
        self.target_state = WorkflowState.INVALID

    # TODO: separate this method to another module
    def commit(self):
        assert self.transaction_state in [
            TransactionState.COORDINATOR_COMMITTING,
            TransactionState.PARTICIPANT_COMMITTING], \
                'Workflow not in prepare state'

        if self.target_state == WorkflowState.STOPPED:
            job_ids = [job.id for job in self.jobs]
            job_scheduler.sleep(job_ids)
            for job in self.jobs:
                job.stop()
                db.session.commit()
        elif self.target_state == WorkflowState.READY:
            job_definitions = self.get_config().job_definitions
            for job_definition in job_definitions:
                job = Job(name=f'{self.name}-{job_definition.name}',
                          job_type=JobType(job_definition.type),
                          config=job_definition.SerializeToString(),
                          workflow_id=self.id,
                          project_id=self.project_id)
                job.set_yaml(job_definition.yaml_template)
                db.session.add(job)
        elif self.target_state == WorkflowState.RUNNING:
            job_ids = [job.id for job in self.jobs]
            for job in self.jobs:
                if job.state != JobState.STARTED:
                    job.state = JobState.READY
            db.session.commit()
            job_scheduler.wakeup(job_ids)

        self.state = self.target_state
        self.target_state = WorkflowState.INVALID
        self.transaction_state = TransactionState.READY

    def log_states(self):
        logging.debug(
            'workflow %d updated to state=%s, target_state=%s, '
            'transaction_state=%s', self.id,
            self.state.name, self.target_state.name,
            self.transaction_state.name)

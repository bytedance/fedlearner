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
from fedlearner_webconsole.proto import (
    common_pb2, workflow_definition_pb2
)
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.job.models import (
    Job, JobState, JobType, JobDependency
)
from fedlearner_webconsole.rpc.client import RpcClient

class WorkflowState(enum.Enum):
    INVALID = 0
    NEW = 1
    READY = 2
    RUNNING = 3
    STOPPED = 4

class RecurType(enum.Enum):
    NONE = 0
    ON_NEW_DATA = 1
    HOURLY = 2
    DAILY = 3
    WEEKLY = 4

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


def _merge_variables(base, new, access_mode):
    new_dict = {i.name: i.value for i in new}
    for var in base:
        if var.access_mode in access_mode and var.name in new_dict:
            var.value = new_dict[var.name]

def _merge_workflow_config(base, new, access_mode):
    _merge_variables(base.variables, new.variables, access_mode)
    if not new.job_definitions:
        return
    assert len(base.job_definitions) == len(new.job_definitions)
    for base_job, new_job in \
            zip(base.job_definitions, new.job_definitions):
        _merge_variables(base_job.variables, new_job.variables, access_mode)



@to_dict_mixin(ignores=['forked_from', 'fork_proposal_config'],
               extras={
                   'config': (lambda wf: wf.get_config()),
               })
class Workflow(db.Model):
    __tablename__ = 'workflow_v2'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey(Project.id))
    config = db.Column(db.Text())
    comment = db.Column(db.String(255))

    forkable = db.Column(db.Boolean, default=False)
    forked_from = db.Column(db.Integer, default=None)
    # index in config.job_defs instead of job's id
    forked_job_indices = db.Column(db.TEXT())
    fork_proposal_config = db.Column(db.TEXT())

    recur_type = db.Column(db.Enum(RecurType), default=RecurType.NONE)
    recur_at = db.Column(db.Interval)
    trigger_dataset = db.Column(db.Integer)
    last_triggered_batch = db.Column(db.Integer)

    job_ids = db.Column(db.TEXT())

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

    owned_jobs = db.relationship('Job', back_populates='workflow')
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

    def get_jobs(self):
        return [Job.query.get(i) for i in self.get_job_ids()]

    def set_forked_job_indices(self, forked_job_indices):
        self.forked_job_indices = ','.join(
            [str(i) for i in forked_job_indices])

    def get_forked_job_indices(self):
        if not self.forked_job_indices:
            return []
        return [int(i) for i in self.forked_job_indices.split(',')]

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
            success = self._prepare_for_ready()

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
            for job in self.owned_jobs:
                job.stop()
        elif self.target_state == WorkflowState.READY:
            self._setup_jobs()
            self.fork_proposal_config = None
        elif self.target_state == WorkflowState.RUNNING:
            for job in self.owned_jobs:
                if not job.get_config().is_manual:
                    job.schedule()

        self.state = self.target_state
        self.target_state = WorkflowState.INVALID
        self.transaction_state = TransactionState.READY

    def _setup_jobs(self):
        job_defs = self.get_config().job_definitions
        name2index = {
            job.name: i for i, job in enumerate(job_defs)
        }

        jobs = []
        if self.forked_from is not None:
            trunk = Workflow.query.get(self.forked_from)
            assert trunk is not None, \
                'Source workflow %d not found'%self.forked_from
        else:
            assert not self.get_forked_job_indices()

        for i, job_def in enumerate(job_defs):
            if i in self.get_forked_job_indices():
                job = Job.query.get(trunk.get_job_ids()[i])
                assert job is not None, \
                    'Job %d not found'%trunk.get_job_ids()[i]
                # TODO: check forked jobs does not depend on non-forked jobs
            else:
                job = Job(name=f'{self.name}-{job_def.name}',
                          job_type=JobType(job_def.type),
                          config=job_def.SerializeToString(),
                          workflow_id=self.id,
                          project_id=self.project_id,
                          state=JobState.STOPPED)
                job.set_yaml_template(job_def.yaml_template)
                db.session.add(job)
            jobs.append(job)
        db.session.commit()

        for i, job in enumerate(jobs):
            if i in self.get_forked_job_indices():
                continue
            for j, dep_def in enumerate(job.get_config().dependencies):
                dep = JobDependency(
                    src_job_id=jobs[name2index[dep_def.source]].id,
                    dst_job_id=job.id,
                    dep_index=j)
                db.session.add(dep)

        self.set_job_ids([job.id for job in jobs])

        db.session.commit()

    def log_states(self):
        logging.debug(
            'workflow %d updated to state=%s, target_state=%s, '
            'transaction_state=%s', self.id,
            self.state.name, self.target_state.name,
            self.transaction_state.name)

    def _get_peer_workflow(self):
        project_config = self.project.get_config()
        # TODO: find coordinator for multiparty
        client = RpcClient(project_config, project_config.participants[0])
        return client.get_workflow(self.name)

    def _prepare_for_ready(self):
        # This is a hack, if config is not set then
        # no action needed
        if self.transaction_state == TransactionState.COORDINATOR_PREPARE:
            # TODO(tjulinfan): validate if the config is legal or not
            return bool(self.config)

        peer_workflow = self._get_peer_workflow()
        if peer_workflow.forked_from:
            base_workflow = Workflow.query.filter(
                Workflow.name == peer_workflow.forked_from).first()
            if base_workflow is None or not base_workflow.forkable:
                return False
            self.forked_from = base_workflow.id
            self.forkable = base_workflow.forkable
            self.set_forked_job_indices(peer_workflow.forked_job_indices)
            config = base_workflow.get_config()
            _merge_workflow_config(
                config, peer_workflow.fork_proposal_config,
                [common_pb2.Variable.PEER_WRITABLE])
            self.set_config(config)
            return True
        return bool(self.config)

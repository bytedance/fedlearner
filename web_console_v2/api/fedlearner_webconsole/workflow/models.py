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
from datetime import datetime
from sqlalchemy.sql import func
from sqlalchemy import UniqueConstraint
from fedlearner_webconsole.db import db, to_dict_mixin
from fedlearner_webconsole.proto import (common_pb2, workflow_definition_pb2)
from fedlearner_webconsole.job.models import (Job, JobState, JobType,
                                              JobDependency)
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


@to_dict_mixin(ignores=['forked_from', 'fork_proposal_config', 'config'],
               extras={
                   'job_ids': (lambda wf: wf.get_job_ids()),
                   'reuse_job_names': (lambda wf: wf.get_reuse_job_names()),
                   'peer_reuse_job_names':
                       (lambda wf: wf.get_peer_reuse_job_names()),
                   'state': (lambda wf: wf.get_state_for_frontend()),
                   'transaction_state':
                       (lambda wf: wf.get_transaction_state_for_frontend()),
               })
class Workflow(db.Model):
    __tablename__ = 'workflow_v2'
    __table_args__ = (UniqueConstraint('uuid', name='uniq_uuid'),
                      UniqueConstraint('name', name='uniq_name'), {
                          'comment': 'workflow_v2',
                          'mysql_engine': 'innodb',
                          'mysql_charset': 'utf8mb4',
                      })
    id = db.Column(db.Integer, primary_key=True, comment='id')
    uuid = db.Column(db.String(64), comment='uuid')
    name = db.Column(db.String(255), comment='name')
    project_id = db.Column(db.Integer, comment='project_id')
    config = db.Column(db.LargeBinary(), comment='config')
    comment = db.Column('cmt',
                        db.String(255),
                        key='comment',
                        comment='comment')

    metric_is_public = db.Column(db.Boolean(),
                                 default=False,
                                 nullable=False,
                                 comment='metric_is_public')

    forkable = db.Column(db.Boolean, default=False, comment='forkable')
    forked_from = db.Column(db.Integer, default=None, comment='forked_from')

    # index in config.job_defs instead of job's id
    reuse_job_names = db.Column(db.TEXT(), comment='reuse_job_names')
    peer_reuse_job_names = db.Column(db.TEXT(), comment='peer_reuse_job_names')
    fork_proposal_config = db.Column(db.LargeBinary(),
                                     comment='fork_proposal_config')

    recur_type = db.Column(db.Enum(RecurType, native_enum=False),
                           default=RecurType.NONE,
                           comment='recur_type')
    recur_at = db.Column(db.Interval, comment='recur_at')
    trigger_dataset = db.Column(db.Integer, comment='trigger_dataset')
    last_triggered_batch = db.Column(db.Integer,
                                     comment='last_triggered_batch')

    job_ids = db.Column(db.TEXT(), comment='job_ids')

    state = db.Column(db.Enum(WorkflowState,
                              native_enum=False,
                              name='workflow_state'),
                      default=WorkflowState.INVALID,
                      comment='state')
    target_state = db.Column(db.Enum(WorkflowState,
                                     native_enum=False,
                                     name='workflow_target_state'),
                             default=WorkflowState.INVALID,
                             comment='target_state')
    transaction_state = db.Column(db.Enum(TransactionState, native_enum=False),
                                  default=TransactionState.READY,
                                  comment='transaction_state')
    transaction_err = db.Column(db.Text(), comment='transaction_err')

    start_at = db.Column(db.Integer, comment='start_at')
    stop_at = db.Column(db.Integer, comment='stop_at')

    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           comment='created_at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           onupdate=func.now(),
                           server_default=func.now(),
                           comment='update_at')

    owned_jobs = db.relationship(
        'Job', primaryjoin='foreign(Job.workflow_id) == Workflow.id')
    project = db.relationship(
        'Project', primaryjoin='Project.id == foreign(Workflow.project_id)')

    def get_state_for_frontend(self):
        if self.state == WorkflowState.RUNNING:
            is_complete = all([job.is_complete() for job in self.owned_jobs])
            if is_complete:
                return 'COMPLETED'
            is_failed = any([job.is_failed() for job in self.owned_jobs])
            if is_failed:
                return 'FAILED'
        return self.state.name

    def get_transaction_state_for_frontend(self):
        # TODO(xiangyuxuan): remove this hack by redesign 2pc
        if (self.transaction_state == TransactionState.PARTICIPANT_PREPARE
                and self.config is not None):
            return 'PARTICIPANT_COMMITTABLE'
        return self.transaction_state.name

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

    def set_reuse_job_names(self, reuse_job_names):
        self.reuse_job_names = ','.join(reuse_job_names)

    def get_reuse_job_names(self):
        if not self.reuse_job_names:
            return []
        return self.reuse_job_names.split(',')

    def set_peer_reuse_job_names(self, peer_reuse_job_names):
        self.peer_reuse_job_names = ','.join(peer_reuse_job_names)

    def get_peer_reuse_job_names(self):
        if not self.peer_reuse_job_names:
            return []
        return self.peer_reuse_job_names.split(',')

    def update_target_state(self, target_state):
        if self.target_state != target_state \
            and self.target_state != WorkflowState.INVALID:
            raise ValueError(f'Another transaction is in progress [{self.id}]')
        if target_state not in [
            WorkflowState.READY, WorkflowState.RUNNING,
            WorkflowState.STOPPED
        ]:
            raise ValueError(f'Invalid target_state {self.target_state}')
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
            logging.warning('Error during update target state in prepare: %s',
                            str(e))
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
            self.stop_at = int(datetime.utcnow().timestamp())
            try:
                for job in self.owned_jobs:
                    job.stop()
            except RuntimeError as e:
                # errors from k8s
                logging.error('Stop workflow %d has Runtime error msg: %s',
                              self.id, e.args)
                return
        elif self.target_state == WorkflowState.READY:
            self._setup_jobs()
            self.fork_proposal_config = None
        elif self.target_state == WorkflowState.RUNNING:
            self.start_at = int(datetime.utcnow().timestamp())
            for job in self.owned_jobs:
                if not job.get_config().is_manual:
                    job.schedule()

        self.state = self.target_state
        self.target_state = WorkflowState.INVALID
        self.transaction_state = TransactionState.READY

    def invalidate(self):
        self.state = WorkflowState.INVALID
        self.target_state = WorkflowState.INVALID
        self.transaction_state = TransactionState.READY
        for job in self.owned_jobs:
            try:
                job.stop()
            except Exception:  # pylint: disable=broad-except
                pass

    def _setup_jobs(self):
        if self.forked_from is not None:
            trunk = Workflow.query.get(self.forked_from)
            assert trunk is not None, \
                'Source workflow %d not found' % self.forked_from
            trunk_job_defs = trunk.get_config().job_definitions
            trunk_name2index = {
                job.name: i
                for i, job in enumerate(trunk_job_defs)
            }
        else:
            assert not self.get_reuse_job_names()

        job_defs = self.get_config().job_definitions
        jobs = []
        reuse_jobs = set(self.get_reuse_job_names())
        for i, job_def in enumerate(job_defs):
            if job_def.name in reuse_jobs:
                assert job_def.name in trunk_name2index, \
                    "Job %s not found in base workflow" % job_def.name
                j = trunk.get_job_ids()[trunk_name2index[job_def.name]]
                job = Job.query.get(j)
                assert job is not None, \
                    'Job %d not found' % j
                # TODO: check forked jobs does not depend on non-forked jobs
            else:
                job = Job(name=f'{self.uuid}-{job_def.name}',
                          job_type=JobType(job_def.job_type),
                          config=job_def.SerializeToString(),
                          workflow_id=self.id,
                          project_id=self.project_id,
                          state=JobState.STOPPED)
                job.set_yaml_template(job_def.yaml_template)
                db.session.add(job)
            jobs.append(job)
        db.session.flush()
        name2index = {job.name: i for i, job in enumerate(job_defs)}
        for i, job in enumerate(jobs):
            if job.get_config().name in reuse_jobs:
                continue
            for j, dep_def in enumerate(job.get_config().dependencies):
                dep = JobDependency(
                    src_job_id=jobs[name2index[dep_def.source]].id,
                    dst_job_id=job.id,
                    dep_index=j)
                db.session.add(dep)

        self.set_job_ids([job.id for job in jobs])

    def log_states(self):
        logging.debug(
            'workflow %d updated to state=%s, target_state=%s, '
            'transaction_state=%s', self.id, self.state.name,
            self.target_state.name, self.transaction_state.name)

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
        if self.forked_from:
            peer_workflow = self._get_peer_workflow()
            base_workflow = Workflow.query.get(self.forked_from)
            if base_workflow is None or not base_workflow.forkable:
                return False
            self.forked_from = base_workflow.id
            self.forkable = base_workflow.forkable
            self.set_reuse_job_names(peer_workflow.peer_reuse_job_names)
            self.set_peer_reuse_job_names(peer_workflow.reuse_job_names)
            config = base_workflow.get_config()
            _merge_workflow_config(config, peer_workflow.fork_proposal_config,
                                   [common_pb2.Variable.PEER_WRITABLE])
            self.set_config(config)
            return True
        return bool(self.config)

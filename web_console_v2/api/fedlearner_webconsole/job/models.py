# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
import datetime
import logging
import enum
import json

from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Index
from fedlearner_webconsole.utils.mixins import to_dict_mixin
from fedlearner_webconsole.db import db
from fedlearner_webconsole.k8s.models import FlApp, Pod, FlAppState
from fedlearner_webconsole.utils.k8s_client import k8s_client
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition


class JobState(enum.Enum):
    # VALID TRANSITION:
    # 1. NEW : init by workflow
    # 2. NEW/STOPPED/COMPLTED/FAILED -> WAITING: triggered by user, run workflow
    # 3. WAITING -> STARTED: triggered by scheduler
    # 4. WAITING -> NEW: triggered by user, stop workflow
    # 4. STARTED -> STOPPED: triggered by user, stop workflow
    # 5. STARTED -> COMPLETED/FAILED: triggered by k8s_watcher
    INVALID = 0 # INVALID STATE
    STOPPED = 1 # STOPPED BY USER
    WAITING = 2 # SCHEDULED, WAITING FOR RUNNING
    STARTED = 3 # RUNNING
    NEW = 4 # BEFORE SCHEDULE
    COMPLETED = 5 # SUCCEEDED JOB
    FAILED = 6 # FAILED JOB


# must be consistent with JobType in proto
class JobType(enum.Enum):
    UNSPECIFIED = 0
    RAW_DATA = 1
    DATA_JOIN = 2
    PSI_DATA_JOIN = 3
    NN_MODEL_TRANINING = 4
    TREE_MODEL_TRAINING = 5
    NN_MODEL_EVALUATION = 6
    TREE_MODEL_EVALUATION = 7


def merge(x, y):
    """Given two dictionaries, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z


@to_dict_mixin(
    extras={
        'state': (lambda job: job.get_state_for_frontend()),
        'pods': (lambda job: job.get_pods_for_frontend()),
        'config': (lambda job: job.get_config()),
        'complete_at': (lambda job: job.get_complete_at())
    })
class Job(db.Model):
    __tablename__ = 'job_v2'
    __table_args__ = (Index('idx_workflow_id', 'workflow_id'), {
        'comment': 'webconsole job',
        'mysql_engine': 'innodb',
        'mysql_charset': 'utf8mb4',
    })
    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   comment='id')
    name = db.Column(db.String(255), unique=True, comment='name')
    job_type = db.Column(db.Enum(JobType, native_enum=False),
                         nullable=False,
                         comment='job type')
    state = db.Column(db.Enum(JobState, native_enum=False),
                      nullable=False,
                      default=JobState.INVALID,
                      comment='state')
    config = db.Column(db.LargeBinary(16777215), comment='config')

    is_disabled = db.Column(db.Boolean(), default=False, comment='is_disabled')

    workflow_id = db.Column(db.Integer, nullable=False, comment='workflow id')
    project_id = db.Column(db.Integer, nullable=False, comment='project id')
    flapp_snapshot = db.Column(db.Text(16777215), comment='flapp snapshot')
    pods_snapshot = db.Column(db.Text(16777215), comment='pods snapshot')
    error_message = db.Column(db.Text(), comment='error message')

    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           comment='created at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           onupdate=func.now(),
                           comment='updated at')
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted at')

    project = db.relationship('Project',
                              primaryjoin='Project.id == '
                              'foreign(Job.project_id)')
    workflow = db.relationship('Workflow',
                               primaryjoin='Workflow.id == '
                               'foreign(Job.workflow_id)')

    def get_config(self):
        if self.config is not None:
            proto = JobDefinition()
            proto.ParseFromString(self.config)
            return proto
        return None

    def set_config(self, proto):
        if proto is not None:
            self.config = proto.SerializeToString()
        else:
            self.config = None

    def _set_snapshot_flapp(self):
        def default(o):
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()
            return str(o)

        flapp = k8s_client.get_flapp(self.name)
        if flapp:
            self.flapp_snapshot = json.dumps(flapp, default=default)
        else:
            self.flapp_snapshot = None

    def get_flapp_details(self):
        if self.state == JobState.STARTED:
            flapp = k8s_client.get_flapp(self.name)
        elif self.flapp_snapshot is not None:
            flapp = json.loads(self.flapp_snapshot)
            # aims to support old job
            if 'flapp' not in flapp:
                flapp['flapp'] = None
            if 'pods' not in flapp and self.pods_snapshot:
                flapp['pods'] = json.loads(self.pods_snapshot)['pods']
        else:
            flapp = {'flapp': None, 'pods': {'items': []}}
        return flapp

    def get_pods_for_frontend(self, include_private_info=True):
        flapp_details = self.get_flapp_details()
        flapp = FlApp.from_json(flapp_details.get('flapp', None))
        pods_json = None
        if 'pods' in flapp_details:
            pods_json = flapp_details['pods'].get('items', None)
        pods = []
        if pods_json is not None:
            pods = [Pod.from_json(p) for p in pods_json]

        # deduplication pods both in pods and flapp
        result = {}
        for pod in flapp.pods:
            result[pod.name] = pod
        for pod in pods:
            result[pod.name] = pod
        return [pod.to_dict(include_private_info) for pod in result.values()]

    def get_state_for_frontend(self):
        return self.state.name

    def is_flapp_failed(self):
        # TODO: make the getter more efficient
        flapp = FlApp.from_json(self.get_flapp_details()['flapp'])
        return flapp.state in [FlAppState.FAILED, FlAppState.SHUTDOWN]

    def is_flapp_complete(self):
        # TODO: make the getter more efficient
        flapp = FlApp.from_json(self.get_flapp_details()['flapp'])
        return flapp.state == FlAppState.COMPLETED

    def get_complete_at(self):
        # TODO: make the getter more efficient
        flapp = FlApp.from_json(self.get_flapp_details()['flapp'])
        return flapp.completed_at

    def stop(self):
        if self.state not in [JobState.WAITING, JobState.STARTED,
                              JobState.COMPLETED, JobState.FAILED]:
            logging.warning('illegal job state, name: %s, state: %s',
                            self.name, self.state)
            return
        if self.state == JobState.STARTED:
            self._set_snapshot_flapp()
            k8s_client.delete_flapp(self.name)
        # state change:
        # WAITING -> NEW
        # STARTED -> STOPPED
        # COMPLETED/FAILED unchanged
        if self.state == JobState.STARTED:
            self.state = JobState.STOPPED
        if self.state == JobState.WAITING:
            self.state = JobState.NEW

    def schedule(self):
        # COMPLETED/FAILED Job State can be scheduled since stop action
        # will not change the state of completed or failed job
        assert self.state in [JobState.NEW, JobState.STOPPED,
                              JobState.COMPLETED, JobState.FAILED]
        self.pods_snapshot = None
        self.flapp_snapshot = None
        self.state = JobState.WAITING

    def start(self):
        assert self.state == JobState.WAITING
        self.state = JobState.STARTED

    def complete(self):
        assert self.state == JobState.STARTED, 'Job State is not STARTED'
        self._set_snapshot_flapp()
        k8s_client.delete_flapp(self.name)
        self.state = JobState.COMPLETED

    def fail(self):
        assert self.state == JobState.STARTED, 'Job State is not STARTED'
        self._set_snapshot_flapp()
        k8s_client.delete_flapp(self.name)
        self.state = JobState.FAILED


class JobDependency(db.Model):
    __tablename__ = 'job_dependency_v2'
    __table_args__ = (Index('idx_src_job_id', 'src_job_id'),
                      Index('idx_dst_job_id', 'dst_job_id'), {
                          'comment': 'record job dependencies',
                          'mysql_engine': 'innodb',
                          'mysql_charset': 'utf8mb4',
                      })
    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   comment='id')
    src_job_id = db.Column(db.Integer, comment='src job id')
    dst_job_id = db.Column(db.Integer, comment='dst job id')
    dep_index = db.Column(db.Integer, comment='dep index')

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
import json
from sqlalchemy.sql import func
from fedlearner_webconsole.db import db, to_dict_mixin
from fedlearner_webconsole.project.adapter import ProjectK8sAdapter
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.k8s_client import get_client
from fedlearner_webconsole.utils.k8s_client import CrdKind
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition


class JobState(enum.Enum):
    INVALID = 0
    STOPPED = 1
    WAITING = 2
    STARTED = 3


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


@to_dict_mixin(extras={
    'flapp': (lambda job: job.get_flapp()),
    'pods': (lambda job: job.get_pods())
})
class Job(db.Model):
    __tablename__ = 'job_v2'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), unique=True)
    job_type = db.Column(db.Enum(JobType), nullable=False)
    state = db.Column(db.Enum(JobState), nullable=False,
                      default=JobState.INVALID)
    yaml = db.Column(db.Text(), nullable=False)
    config = db.Column(db.Text(), nullable=False)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow_v2.id'),
                            nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey(Project.id),
                           nullable=False)
    flapp_snapshot = db.Column(db.Text())
    pods_snapshot = db.Column(db.Text())
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           server_onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True))

    project = db.relationship(Project)
    workflow = db.relationship('Workflow')
    _k8s_client = get_client()

    def get_config(self):
        if self.config is not None:
            proto = JobDefinition()
            proto.ParseFromString(self.config)
            return proto
        return None

    def _set_snapshot_flapp(self):
        project_adapter = ProjectK8sAdapter(self.project)
        flapp = self._k8s_client.get_custom_object(
            CrdKind.FLAPP, self.name, project_adapter.get_namespace())
        self.flapp_snapshot = json.dumps(flapp)

    def _set_snapshot_pods(self):
        project_adapter = ProjectK8sAdapter(self.project)
        pods = self._k8s_client.list_resource_of_custom_object(
            CrdKind.FLAPP, self.name, 'pods', project_adapter.get_namespace())
        self.pods_snapshot = json.dumps(pods)

    def get_flapp(self):
        # TODO: remove update snapshot to scheduler
        if self.state == JobState.STARTED:
            self._set_snapshot_flapp()
        return json.loads(self.flapp_snapshot)

    def get_pods(self):
        if self.state == JobState.STARTED:
            self._set_snapshot_pods()
        return json.loads(self.pods_snapshot)

    def is_complete(self):
        return self.get_flapp()['status']['appState'] == 'FLStateComplete'

    def stop(self):
        project_adapter = ProjectK8sAdapter(self.project)
        if self.state == JobState.STARTED:
            self._set_snapshot_flapp()
            self._set_snapshot_pods()
            self._k8s_client.delete_custom_object(
                CrdKind.FLAPP, self.name, project_adapter.get_namespace())
        self.state = JobState.STOPPED

    def schedule(self):
        assert self.state == JobState.STOPPED
        self.pods_snapshot = None
        self.flapp_snapshot = None
        self.state = JobState.WAITING

    def start(self):
        self.state = JobState.STARTED

    def set_yaml(self, yaml_template):
        self.yaml = yaml_template


class JobDependency(db.Model):
    __tablename__ = 'job_dependency_v2'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    src_job_id = db.Column(db.Integer, index=True)
    dst_job_id = db.Column(db.Integer, index=True)
    dep_index = db.Column(db.Integer)

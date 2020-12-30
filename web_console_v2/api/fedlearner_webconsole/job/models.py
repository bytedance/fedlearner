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
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.k8s_client import get_client
from fedlearner_webconsole.proto.job_pb2 import Context
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDependency
class JobStatus(enum.Enum):
    UNSPECIFIED = 'NEW'
    PRERUN = 'PRERUN'
    STARTED = 'STARTED'
    STOPPED = 'STOPPED'




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
    job_type = db.Column(db.String(16), nullable=False)
    status = db.Column(db.Enum(JobStatus), nullable=False)
    yaml = db.Column(db.Text(), nullable=False)

    workflow_id = db.Column(db.Integer, db.ForeignKey(Workflow.id),
                            nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey(Project.id),
                           nullable=False)
    # dependencies and successors in proto form
    context = db.Column(db.Text())
    flapp_snapshot = db.Column(db.Text())
    pods_snapshot = db.Column(db.Text())
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           server_onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True))
    _project_adapter = ProjectK8sAdapter(project_id)
    _k8s_client = get_client()

    def get_context(self):
        if self.context is not None:
            proto = Context()
            proto.ParseFromString(self.context)
            return proto
        return None

    def _set_snapshot_flapp(self):
        flapp = json.dumps(self._k8s_client.get_flapp(self.
                           _project_adapter.get_namespace(), self.name))
        self.flapp_snapshot = json.dumps(flapp)

    def _set_snapshot_pods(self):
        flapp = json.dumps(self._k8s_client.get_pods(self.
                           _project_adapter.get_namespace(), self.name))
        self.flapp_snapshot = json.dumps(flapp)

    def get_flapp(self):
        if self.status == JobStatus.STARTED:
            self._set_snapshot_flapp()
        return json.loads(self.flapp_snapshot)

    def get_pods(self):
        if self.status == JobStatus.STARTED:
            self._set_snapshot_pods()
        return json.loads(self.pods_snapshot)

    def run(self):
        if self.status != JobStatus.PRERUN:
            return
        context = self.get_context()
        dependencies = context.dependencies
        for dependency in dependencies:
            job = Job.query.filter_by(name=dependency.source).first()
            if job is None or job.status != JobStatus.STARTED:
                return
            if dependency.type == JobDependency.ON_COMPLETE:
                if job.get_flapp()['status']['appState'] != 'FLStateComplete':
                    return
        self.status = JobStatus.STARTED
        self._k8s_client.create_flapp(self._project_adapter.
                                      get_namespace(), self.yaml)
        db.session.commit()

    def stop(self):
        if self.status == JobStatus.STARTED:
            self._set_snapshot_flapp()
            self._set_snapshot_pods()
            self._k8s_client.deleteFLApp(self.project_adapter.
                                         get_namespace(), self.name)
        self.status = JobStatus.STOPPED
        db.session.commit()

    def set_yaml(self, yaml_template, job_config):
        yaml = merge(yaml_template,
                     self._project_adapter.get_global_job_spec())
        # TODO: complete yaml

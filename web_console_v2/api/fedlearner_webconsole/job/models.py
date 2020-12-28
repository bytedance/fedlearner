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
from fedlearner_webconsole.exceptions import ResourceConflictException


class JobStatus(enum.Enum):
    UNSPECIFIED = 'NEW'
    STARTED = 'STARTED'
    STOPPED = 'STOPPED'



class ProjectK8sAdapter():
    def get_namespace(self):
        pass

    def get_storage_root_path(self):
        pass

    def get_global_job_spec(self):
        pass

    def get_global_replica_spec(self):
        pass

    def get_worker_grpc_spec(self):
        pass


def merge_two_dicts(x, y):
    """Given two dictionaries, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z


@to_dict_mixin(extras={
    'status': (lambda job: job.status.value),
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

    workflow_id = db.Column(db.Integer, nullable=False, index=True)
    project_id = db.Column(db.Integer, nullable=False)

    flapp_snapshot = db.Column(db.Text())
    pods_snapshot = db.Column(db.Text())
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           server_onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True))
    project_adapter = ProjectK8sAdapter(id)


    def set_snapshot_flapp(self):
        flapp = json.dumps('k8s.get_flapp(self.'
                           'project_adapter.get_namespace(), self.name)')
        self.flapp_snapshot = json.dumps(flapp)

    def set_snapshot_pods(self):
        flapp = json.dumps('k8s.get_pods(self.'
                           'project_adapter.get_namespace(), self.name)')
        self.flapp_snapshot = json.dumps(flapp)



    def get_flapp(self):
        if self.status == JobStatus.STARTED:
            self.set_snapshot_flapp()
        return json.loads(self.flapp_snapshot)

    def get_pods(self):
        if self.status == JobStatus.STARTED:
            self.set_snapshot_pods()
        return json.loads(self.pods_snapshot)

    def run(self):
        if  self.status == JobStatus.STARTED:
            raise ResourceConflictException('Job has been started')
        self.status = JobStatus.STARTED
        # k8s.createFLApp(self.project_adapter.
        # get_namespace(), self.yaml)


    def stop(self):
        if self.status == JobStatus.STOPPED:
            raise ResourceConflictException('Job has stopped')
        self.status = JobStatus.STOPPED
        self.set_snapshot_pods()
        self.set_snapshot_flapp()
        # k8s.deleteFLApp(self.project_adapter.
        # get_namespace(), name)

    def set_yaml(self, yaml_template, job_config):
        yaml = merge_two_dicts(yaml_template, self.project_adapter.get_global_job_spec())
        yaml = merge_two_dicts(yaml, self.project_adapter)



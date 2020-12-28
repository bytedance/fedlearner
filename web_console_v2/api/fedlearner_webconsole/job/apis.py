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
from flask_restful import Resource, request
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.exceptions import NotFoundException,\
    InvalidArgumentException
class JobsApi(Resource):
    def get(self, workflow_id):
        return{'data': [row.to_dict() for row in
                        Job.query.filter_by(workflow_id=workflow_id).all()]}
class JobApi(Resource):
    def get(self, job_id):
        job = Job.query.filter_by(job=job_id).first()
        if job is None:
            raise NotFoundException()
        return {'data': job.to_dict()}


class PodLogApi(Resource):
    def get(self, pod_name):
        if 'start_time' not in request.args:
            raise InvalidArgumentException('start_time is required')
        return {'data': "es.queryLog('filebeat-*', '',"
                        " pod_name, start_time, Date.now())"}

class PodContainerApi(Resource):
    def get(self, pod_name):
        base = "k8s.getBaseUrl()"
        container_id = "k8s.getWebshellSession(" \
                       "namespace, pod_name, 'tensorflow')"
        return {'data': {'id': container_id}}

def initialize_job_apis(api):
    api.add_resource(JobsApi, '/jobs/<int:workflow_id>')
    api.add_resource(JobApi, '/jobs/job/<int:job_id>')
    api.add_resource(PodLogApi, '/jobs/job/pod/<string:pod_name>/log')

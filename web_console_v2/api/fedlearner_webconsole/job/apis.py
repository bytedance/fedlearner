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
import time
from google.protobuf.json_format import MessageToDict
from flask_restful import Resource, request
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.job.es import es
from fedlearner_webconsole.exceptions import NotFoundException, \
    InvalidArgumentException
from fedlearner_webconsole.k8s_client import get_client
from fedlearner_webconsole.project.adapter import ProjectK8sAdapter
from fedlearner_webconsole.rpc.client import RpcClient

class JobsApi(Resource):
    def get(self, workflow_id):
        # TODO: merge this to get workflow api
        if 'peer_jobs' not in request.args:
            raise InvalidArgumentException('peer_jobs flag required')
        workflow = Workflow.query.filter_by(id=workflow_id).first()
        if workflow is None:
            raise NotFoundException()
        if request.args['peer_jobs']:
            project_config = workflow.project.get_config()
            peer_jobs = {}
            for party in project_config.participants:
                client = RpcClient(project_config, party)
                resp = client.get_jobs(workflow.name)
                peer_jobs[party.name] = MessageToDict(
                            resp.jobs,
                            preserving_proto_field_name=True,
                            including_default_value_fields=True)
            return {'data': {'self': [row.to_dict() for row in workflow.jobs],
                             'peers': peer_jobs}}

        return {'data': {'self': [row.to_dict() for row in workflow.jobs]}}


class JobApi(Resource):
    def get(self, job_id):
        job = Job.query.filter_by(job=job_id).first()
        if job is None:
            raise NotFoundException()
        return {'data': job.to_dict()}

    # TODO: manual start jobs


class PodLogApi(Resource):
    def get(self, pod_name):
        if 'start_time' not in request.args:
            raise InvalidArgumentException('start_time is required')
        return {'data': es.query_log('filebeat-*', '', pod_name,
                                     request.args['start_time'],
                                     int(time.time() * 1000))}


class PodContainerApi(Resource):
    def get(self, job_id, pod_name):
        k8s = get_client()
        base = k8s.get_base_url()
        container_id = k8s.get_webshell_session(ProjectK8sAdapter(job_id)
                                                .get_namespace(), pod_name,
                                                'tensorflow')
        return {'data': {'id': container_id, 'base': base}}


def initialize_job_apis(api):
    api.add_resource(JobsApi, '/workflows/<int:workflow_id>/jobs')
    api.add_resource(JobApi, '/jobs/<int:job_id>')
    api.add_resource(PodLogApi,
                     '/jobs/<int:job_id>/pods/<string:pod_name>/log')
    api.add_resource(PodContainerApi,
                     '/jobs/<int:job_id>/pods/<string:pod_name>/container')

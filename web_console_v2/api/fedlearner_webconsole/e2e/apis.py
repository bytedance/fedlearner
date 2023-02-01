# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from flask_restful import Api, Resource
from kubernetes.client import ApiException
from marshmallow import validate, post_load
from webargs.flaskparser import use_args
from flasgger import Schema, fields

from fedlearner_webconsole.db import db
from fedlearner_webconsole.e2e.controllers import ROLES_MAPPING, get_job, get_job_logs, initiate_all_tests
from fedlearner_webconsole.exceptions import NotFoundException, InvalidArgumentException
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.e2e_pb2 import InitiateE2eJobsParameter
from fedlearner_webconsole.swagger.models import schema_manager
from fedlearner_webconsole.utils.flask_utils import make_flask_response
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.utils.decorators.pp_flask import admin_required


class E2eJobsApi(Resource):

    @credentials_required
    @admin_required
    def get(self, job_name: str):
        """Get an existing job
        ---
        tags:
          - e2e
        description: get a job
        parameters:
        - in: path
          name: job_name
          required: true
          schema:
            type: string
          description: The name of the job
        responses:
          200:
            description: The corresponding job
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    job_name:
                      type: string
                      description: The name of the job
                    status:
                      type: object
                      description: The status of the job
                    log:
                      type: array
                      items:
                        type: string
                      description: The log of the job; if the job is still active, an empty string is returned
          404:
            description: The job is not found
        """
        try:
            status = get_job(job_name)['status']
        except ApiException as e:
            raise NotFoundException(f'failed to find job {job_name}') from e
        # if the pod is still running, do not query for logs
        log = get_job_logs(job_name) if 'active' not in status else []
        return make_flask_response(data={'job_name': job_name, 'status': status, 'log': log})


# If schema is defined as "...Schema", the last "Schema" will be deleted, so the reference to this schema
# is "#/definitions/InitiateE2eJobsParameter"
class InitiateE2eJobsParameterSchema(Schema):
    role = fields.String(required=True, validate=validate.OneOf(ROLES_MAPPING.keys()))
    name_prefix = fields.String(required=True, validate=validate.Length(min=5))
    project_name = fields.String(required=True, validate=validate.Length(min=1))
    e2e_image_uri = fields.String(required=True, validate=lambda x: 'fedlearner_e2e:' in x)
    fedlearner_image_uri = fields.String(required=True, validate=lambda x: 'fedlearner:' in x)
    platform_endpoint = fields.String(required=False,
                                      load_default='http://fedlearner-fedlearner-web-console-v2-http:1989',
                                      validate=validate.URL(require_tld=False))

    @post_load
    def make_initiate_e2e_jobs_parameter(self, data, **kwargs) -> InitiateE2eJobsParameter:
        del kwargs
        return InitiateE2eJobsParameter(**data)


class InitiateE2eJobsApi(Resource):

    @credentials_required
    @admin_required
    @use_args(InitiateE2eJobsParameterSchema(), location='json')
    def post(self, params: InitiateE2eJobsParameter):
        """Initiate a series of E2e jobs
        ---
        tags:
          - e2e
        description: initiate a series of E2e jobs
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/InitiateE2eJobsParameter'
        responses:
          201:
            description: Jobs are launched and job names are returned
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: object
                    properties:
                      job_type:
                        type: string
                      job_name:
                        type: string
        """
        with db.session_scope() as session:
            project = session.query(Project).filter(Project.name == params.project_name).first()
            if project is None:
                raise InvalidArgumentException(f'failed to find project with name={params.project_name}')
        try:
            jobs = initiate_all_tests(params)
        except ValueError as e:
            raise InvalidArgumentException(str(e)) from e
        return make_flask_response(jobs)


def initialize_e2e_apis(api: Api):
    api.add_resource(E2eJobsApi, '/e2e_jobs/<string:job_name>')
    api.add_resource(InitiateE2eJobsApi, '/e2e_jobs:initiate')
    schema_manager.append(InitiateE2eJobsParameterSchema)

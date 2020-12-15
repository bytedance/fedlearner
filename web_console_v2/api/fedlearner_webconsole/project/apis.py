# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

from enum import Enum
from uuid import uuid4
from http import HTTPStatus
from flask_restful import Resource, Api, abort, reqparse
from google.protobuf.json_format import ParseDict
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.project_pb2 import Project as ProjectProto, Certificate
from fedlearner_webconsole.utils.k8s_client import K8sClient
from fedlearner_webconsole.project.add_on import _parse_certificates, _create_add_on

_CERTIFICATE_FILE_NAMES = [
    'client/client.pem', 'client/client.key', 'client/intermediate.pem', 'client/root.pem',
    'server/server.pem', 'server/server.key', 'server/intermediate.pem', 'server/root.pem'
]


class ErrorMessage(Enum):
    PARAM_FORMAT_ERROR = 'Format of parameter {} is wrong: {}'
    NAME_CONFLICT = 'Project name {} has been used.'


class ProjectsApi(Resource):

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True, type=str,
                            help=ErrorMessage.PARAM_FORMAT_ERROR.value.format('name', 'Empty'))
        parser.add_argument('config', required=True, type=dict,
                            help=ErrorMessage.PARAM_FORMAT_ERROR.value.format('config', 'Empty'))
        parser.add_argument('comment')

        data = parser.parse_args()
        name = data['name']
        config = data['config']
        comment = data['comment']

        if Project.query.filter_by(name=name).first() is not None:
            abort(HTTPStatus.BAD_REQUEST,
                  message=ErrorMessage.NAME_CONFLICT.value.format(name))

        if config.get('participants') is None:
            abort(HTTPStatus.BAD_REQUEST,
                  message=ErrorMessage.PARAM_FORMAT_ERROR.value.format('participants', 'Empty'))
        if len(config.get('participants')) == 0:
            abort(HTTPStatus.BAD_REQUEST,
                  message=ErrorMessage.PARAM_FORMAT_ERROR.value.format('participants', 'Length 0'))
        elif len(config.get('participants')) > 1:
            # TODO: remove limit in schema after operator supports multiple participants
            abort(HTTPStatus.BAD_REQUEST,
                  message='Currently not support multiple participants.')

        certificates = {}
        for participant in config.get('participants'):
            if {'name', 'domain_name', 'url'} <= participant.keys():
                if participant.get('certificates') is not None:
                    current_cert = _parse_certificates(participant.get('certificates'))
                    # check validation
                    for file_name in _CERTIFICATE_FILE_NAMES:
                        if current_cert.get(file_name) is None:
                            abort(HTTPStatus.BAD_REQUEST,
                                  message=ErrorMessage.PARAM_FORMAT_ERROR
                                  .value.format('certificates', '{} not existed'.format(file_name)))
                    certificates[participant.get('domain_name')] = participant.get('certificates')
                    participant.pop('certificates')
                # format participant to proto structure
                # TODO: fill other fields
                participant['grpc_spec'] = {
                    'url': participant.get('url')
                }
                participant.pop('url')
            else:
                abort(HTTPStatus.BAD_REQUEST,
                      message=ErrorMessage.PARAM_FORMAT_ERROR.value
                      .format('participants', 'Participant must have name, domain_name and url.'))

        new_project = Project()
        # generate token
        # If users send a token, then use it instead.
        # If `token` is None, generate a new one by uuid.
        token = config.get('token', uuid4().hex)
        config['token'] = token

        # check format of config
        try:
            new_project.set_config(ParseDict(config, ProjectProto()))
        except Exception as e:
            abort(HTTPStatus.BAD_REQUEST,
                  message=ErrorMessage.PARAM_FORMAT_ERROR.value.format('config', e))
        new_project.set_certificate(ParseDict({'certificate': certificates},
                                              Certificate()))
        new_project.name = name
        new_project.token = token
        new_project.comment = comment

        # following operations will change the state of k8s and db
        try:
            k8s_client = K8sClient()
            for domain_name, certificate in certificates.items():
                _create_add_on(k8s_client, domain_name, certificate)

            db.session.add(new_project)
            db.session.commit()
        except Exception as e:
            abort(HTTPStatus.INTERNAL_SERVER_ERROR, msg=e)

        return {
            'data': new_project.to_dict(),
            'message': ''
        }


def initialize_project_apis(api: Api):
    api.add_resource(ProjectsApi, '/projects')

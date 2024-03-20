# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
# pylint: disable=raise-missing-from

import re
from enum import Enum
from uuid import uuid4

from sqlalchemy.sql import func
from flask import request
from flask_restful import Resource, Api, reqparse
from google.protobuf.json_format import ParseDict

from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.common_pb2 import Variable, StatusCode
from fedlearner_webconsole.proto.project_pb2 \
    import Project as ProjectProto, CertificateStorage, \
    Participant as ParticipantProto
from fedlearner_webconsole.project.add_on \
    import parse_certificates, verify_certificates, create_add_on
from fedlearner_webconsole.exceptions \
    import InvalidArgumentException, NotFoundException
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.utils.decorators import jwt_required
from fedlearner_webconsole.utils.k8s_client import k8s_client
from fedlearner_webconsole.workflow.models import Workflow

_CERTIFICATE_FILE_NAMES = [
    'client/client.pem', 'client/client.key', 'client/intermediate.pem',
    'client/root.pem', 'server/server.pem', 'server/server.key',
    'server/intermediate.pem', 'server/root.pem'
]

_URL_REGEX = r'(?:^((?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])(?:\.' \
             r'(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])){3})(?::+' \
             r'(\d+))?$)|(?:^\[((?:(?:[0-9a-fA-F:]){1,4}(?:(?::(?:[0-9a-fA-F]' \
             r'){1,4}|:)){2,7})+)\](?::+(\d+))?|((?:(?:[0-9a-fA-F:]){1,4}(?:(' \
             r'?::(?:[0-9a-fA-F]){1,4}|:)){2,7})+)$)'


class ErrorMessage(Enum):
    PARAM_FORMAT_ERROR = 'Format of parameter {} is wrong: {}'
    NAME_CONFLICT = 'Project name {} has been used.'


class ProjectsApi(Resource):
    @jwt_required()
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name',
                            required=True,
                            type=str,
                            help=ErrorMessage.PARAM_FORMAT_ERROR.value.format(
                                'name', 'Empty'))
        parser.add_argument('config',
                            required=True,
                            type=dict,
                            help=ErrorMessage.PARAM_FORMAT_ERROR.value.format(
                                'config', 'Empty'))
        parser.add_argument('comment')
        data = parser.parse_args()
        name = data['name']
        config = data['config']
        comment = data['comment']

        if Project.query.filter_by(name=name).first() is not None:
            raise InvalidArgumentException(
                details=ErrorMessage.NAME_CONFLICT.value.format(name))

        if config.get('participants') is None:
            raise InvalidArgumentException(
                details=ErrorMessage.PARAM_FORMAT_ERROR.value.format(
                    'participants', 'Empty'))
        if len(config.get('participants')) != 1:
            # TODO: remove limit after operator supports multiple participants
            raise InvalidArgumentException(
                details='Currently not support multiple participants.')

        # exact configuration from variables
        # TODO: one custom host for one participant
        grpc_ssl_server_host = None
        egress_host = None
        for variable in config.get('variables', []):
            if variable.get('name') == 'GRPC_SSL_SERVER_HOST':
                grpc_ssl_server_host = variable.get('value')
            if variable.get('name') == 'EGRESS_HOST':
                egress_host = variable.get('value')

        # parse participant
        certificates = {}
        for participant in config.get('participants'):
            if 'name' not in participant.keys() or \
                'domain_name' not in participant.keys():
                raise InvalidArgumentException(
                    details=ErrorMessage.PARAM_FORMAT_ERROR.value.format(
                        'participants', 'Participant must have name and '
                        'domain_name.'))
            domain_name = participant.get('domain_name')
            # Grpc spec
            participant['grpc_spec'] = {
                'authority':
                egress_host or '{}-client-auth.com'.format(domain_name[:-4])
            }

            if participant.get('certificates'):
                # If users use web console to create add-on,
                # peer url must be given
                if 'url' not in participant.keys():
                    raise InvalidArgumentException(
                        details=ErrorMessage.PARAM_FORMAT_ERROR.value.format(
                            'participants', 'Participant must have url.'))
                if re.match(_URL_REGEX, participant.get('url')) is None:
                    raise InvalidArgumentException('URL pattern is wrong')

                current_cert = parse_certificates(
                    participant.get('certificates'))
                success, err = verify_certificates(current_cert)
                if not success:
                    raise InvalidArgumentException(err)
                certificates[domain_name] = {'certs': current_cert}
            if 'certificates' in participant.keys():
                participant.pop('certificates')

        new_project = Project()
        # generate token
        # If users send a token, then use it instead.
        # If `token` is None, generate a new one by uuid.
        config['name'] = name
        token = config.get('token', uuid4().hex)
        config['token'] = token

        # check format of config
        try:
            new_project.set_config(ParseDict(config, ProjectProto()))
        except Exception as e:
            raise InvalidArgumentException(
                details=ErrorMessage.PARAM_FORMAT_ERROR.value.format(
                    'config', e))
        new_project.set_certificate(
            ParseDict({'domain_name_to_cert': certificates},
                      CertificateStorage()))
        new_project.name = name
        new_project.token = token
        new_project.comment = comment

        # create add on
        for participant in new_project.get_config().participants:
            if participant.domain_name in\
                new_project.get_certificate().domain_name_to_cert.keys():
                _create_add_on(
                    participant,
                    new_project.get_certificate().domain_name_to_cert[
                        participant.domain_name], grpc_ssl_server_host)
        try:
            new_project = db.session.merge(new_project)
            db.session.commit()
        except Exception as e:
            raise InvalidArgumentException(details=str(e))

        return {'data': new_project.to_dict()}

    @jwt_required()
    def get(self):
        # TODO: Not count soft-deleted workflow
        projects = db.session.query(
                Project, func.count(Workflow.id).label('num_workflow'))\
            .join(Workflow, Workflow.project_id == Project.id, isouter=True)\
            .group_by(Project.id)\
            .all()
        result = []
        for project in projects:
            project_dict = project.Project.to_dict()
            project_dict['num_workflow'] = project.num_workflow
            result.append(project_dict)
        return {'data': result}


class ProjectApi(Resource):
    @jwt_required()
    def get(self, project_id):
        project = Project.query.filter_by(id=project_id).first()
        if project is None:
            raise NotFoundException(
                f'Failed to find project: {project_id}')
        return {'data': project.to_dict()}

    @jwt_required()
    def patch(self, project_id):
        project = Project.query.filter_by(id=project_id).first()
        if project is None:
            raise NotFoundException(
                f'Failed to find project: {project_id}')
        config = project.get_config()
        if request.json.get('token') is not None:
            new_token = request.json.get('token')
            config.token = new_token
            project.token = new_token
        if request.json.get('variables') is not None:
            del config.variables[:]
            config.variables.extend([
                ParseDict(variable, Variable())
                for variable in request.json.get('variables')
            ])

        # exact configuration from variables
        grpc_ssl_server_host = None
        egress_host = None
        for variable in config.variables:
            if variable.name == 'GRPC_SSL_SERVER_HOST':
                grpc_ssl_server_host = variable.value
            if variable.name == 'EGRESS_HOST':
                egress_host = variable.value

        if request.json.get('participant_name'):
            config.participants[0].name = request.json.get('participant_name')

        if request.json.get('comment'):
            project.comment = request.json.get('comment')

        for participant in config.participants:
            if participant.domain_name in\
                project.get_certificate().domain_name_to_cert.keys():
                _create_add_on(
                    participant,
                    project.get_certificate().domain_name_to_cert[
                        participant.domain_name], grpc_ssl_server_host)
            if egress_host:
                participant.grpc_spec.authority = egress_host
        project.set_config(config)
        try:
            db.session.commit()
        except Exception as e:
            raise InvalidArgumentException(details=e)
        return {'data': project.to_dict()}


class CheckConnectionApi(Resource):
    @jwt_required()
    def post(self, project_id):
        project = Project.query.filter_by(id=project_id).first()
        if project is None:
            raise NotFoundException(
                f'Failed to find project: {project_id}')
        success = True
        details = []
        # TODO: Concurrently check
        for participant in project.get_config().participants:
            result = self.check_connection(project.get_config(), participant)
            success = success & (result.code == StatusCode.STATUS_SUCCESS)
            if result.code != StatusCode.STATUS_SUCCESS:
                details.append(result.msg)
        return {'data': {'success': success, 'details': details}}

    def check_connection(self, project_config: ProjectProto,
                         participant_proto: ParticipantProto):
        client = RpcClient(project_config, participant_proto)
        return client.check_connection().status


def initialize_project_apis(api: Api):
    api.add_resource(ProjectsApi, '/projects')
    api.add_resource(ProjectApi, '/projects/<int:project_id>')
    api.add_resource(CheckConnectionApi,
                     '/projects/<int:project_id>/connection_checks')


def _create_add_on(participant, certificate, grpc_ssl_server_host=None):
    if certificate is None:
        return
    # check validation
    for file_name in _CERTIFICATE_FILE_NAMES:
        if certificate.certs.get(file_name) is None:
            raise InvalidArgumentException(
                details=ErrorMessage.PARAM_FORMAT_ERROR.value.format(
                    'certificates', '{} not existed'.format(file_name)))
    try:
        create_add_on(k8s_client, participant.domain_name, participant.url,
                      certificate.certs, grpc_ssl_server_host)
    except RuntimeError as e:
        raise InvalidArgumentException(details=str(e))

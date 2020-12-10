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

import tarfile
import io
import os
import json
from enum import Enum
from uuid import uuid4
from http import HTTPStatus
from base64 import b64encode, b64decode
from flask_restful import Resource, Api, abort
from flask import request
from google.protobuf.json_format import ParseDict
from jsonschema.exceptions import ValidationError
from jsonschema import validate
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.project_pb2 import Project as ProjectProto, Certificate
from fedlearner_webconsole.utils.k8s_client import K8sClient

_CERTIFICATE_FILE_NAMES = [
    'client/client.pem', 'client/client.key', 'client/intermediate.pem', 'client/root.pem',
    'server/server.pem', 'server/server.key', 'server/intermediate.pem', 'server/root.pem'
]


class ErrorMessage(Enum):
    PARAM_FORMAT_ERROR = 'Format of parameter {} is wrong: {}'
    NAME_CONFLICT = 'Project name {} has been used.'


class ProjectsApi(Resource):

    def post(self):
        # TODO: remove limit in schema after operator supports multiple participants
        error_msg = _check_schema(request_body=request.get_json(), schema_name='create_project')
        if error_msg is not None:
            abort(HTTPStatus.BAD_REQUEST,
                  msg=ErrorMessage.PARAM_FORMAT_ERROR.value.format('', error_msg))

        name = request.json.get('name')
        config = request.json.get('config')
        comment = request.json.get('comment')

        if Project.query.filter_by(name=name).first() is not None:
            abort(HTTPStatus.BAD_REQUEST,
                  msg=ErrorMessage.NAME_CONFLICT.value.format(name))

        # extract certificates
        certificates = {}
        for participant in config.get('participants'):
            if participant.get('certificates') is not None:
                certificates[participant.get('domain_name')] = participant.get('certificates')
                participant.pop('certificates')

            # format participant to proto structure
            participant['grpc_spec'] = {
                'url': participant.get('url')
            }
            participant.pop('url')

        new_project = Project()
        # generate token
        # If users send a token, then use it instead.
        token = config.get('token', uuid4().hex)
        config['token'] = token

        # check format of config
        try:
            new_project.set_config(ParseDict(config, ProjectProto()))
        except Exception as e:
            abort(HTTPStatus.BAD_REQUEST,
                  msg=ErrorMessage.PARAM_FORMAT_ERROR.value.format('config', e))
        new_project.set_certificate(ParseDict({'certificate': certificates},
                                              Certificate()))
        new_project.name = name
        new_project.token = token
        new_project.comment = comment

        # following operations will change the state of k8s and db
        try:
            k8s_client = K8sClient()
            for domain_name, certificate in certificates.items():
                _create_add_on(k8s_client, certificate, domain_name)

            db.session.add(new_project)
            db.session.commit()
        except Exception as e:
            abort(HTTPStatus.INTERNAL_SERVER_ERROR, msg=e)

        return {
            'data': {
                'id': new_project.id,
                'token': new_project.token,
                'created_at': new_project.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                'updated_at': new_project.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            },
            'msg': ''
        }


def _check_schema(request_body, schema_name):
    """Checks if request body is valid or not, returns error messages."""
    current_directory = os.path.dirname(os.path.realpath(__file__))
    schema_path = os.path.join(current_directory, 'schema/{}.json'.format(schema_name))
    if os.path.isfile(schema_path):
        with open(schema_path, 'r') as file:
            schema = json.load(file)
        try:
            validate(request_body, schema)
        except ValidationError as error:
            return error.message
    else:
        return 'Schema not found'


def _convert_certificates(encoded_gz):
    """
    convert certificates from base64-encoded string to a dict
    Args:
        encoded_gz: A base64-encoded string from a `.gz` file. It should include files in _CERTIFICATE_FILE_NAMES

    Returns:
        dict: key is the file name, value is the content

    """
    binary_gz = io.BytesIO(b64decode(encoded_gz))
    gz = tarfile.open(fileobj=binary_gz)
    certificates = {}
    for file in gz.getmembers():
        if file.isfile():
            # raw file name is like `fl-test.com/client/client.pem`
            certificates[file.name.split('/', 1)[-1]] = str(b64encode(gz.extractfile(file).read()),
                                                            encoding='utf-8')
    # check validation
    for file_name in _CERTIFICATE_FILE_NAMES:
        if certificates.get(file_name) is None:
            raise RuntimeError(ErrorMessage.PARAM_FORMAT_ERROR.value.format(
                'certificates', '{} not existed'.format(file_name)))
    return certificates


def _create_add_on(client, encoded_cert, domain_name):
    """Create add on and upgrade nginx-ingress and operator"""
    # TODO
    pass


def initialize_project_apis(api: Api):
    api.add_resource(ProjectsApi, '/projects')

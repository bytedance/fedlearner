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

import logging
import os
import json
import tempfile
import grpc
from flask import request, send_file
from typing import Optional
from http import HTTPStatus
from envs import Envs
from sqlalchemy import Column
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement
from werkzeug.utils import secure_filename
from flask_restful import Resource
from google.protobuf.json_format import ParseDict
from marshmallow import Schema, post_load, fields, validate
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.audit.decorators import emits_event
from fedlearner_webconsole.utils.decorators.pp_flask import admin_required, input_validator
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.utils.file_tree import FileTreeBuilder
from fedlearner_webconsole.utils.filtering import SupportedField, FieldType, FilterBuilder, SimpleExpression
from fedlearner_webconsole.utils.sorting import SorterBuilder, SortExpression, parse_expression
from fedlearner_webconsole.utils.paginate import paginate
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmParameter
from fedlearner_webconsole.proto.filtering_pb2 import FilterOp
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.algorithm.fetcher import AlgorithmFetcher
from fedlearner_webconsole.algorithm.utils import algorithm_project_path, algorithm_path, check_algorithm_file
from fedlearner_webconsole.algorithm.preset_algorithms.preset_algorithm_service \
    import create_algorithm_if_not_exists
from fedlearner_webconsole.algorithm.service import AlgorithmProjectService, PendingAlgorithmService, AlgorithmService
from fedlearner_webconsole.swagger.models import schema_manager
from fedlearner_webconsole.utils.file_operator import FileOperator
from fedlearner_webconsole.utils.pp_datetime import now
from fedlearner_webconsole.utils.decorators.pp_flask import use_args, use_kwargs
from fedlearner_webconsole.utils.flask_utils import make_flask_response, get_current_user, FilterExpField
from fedlearner_webconsole.algorithm.models import Algorithm, AlgorithmProject, ReleaseStatus, Source, AlgorithmType, \
    PendingAlgorithm, normalize_path
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.exceptions import NoAccessException, NotFoundException, InvalidArgumentException, \
    UnauthorizedException, ResourceConflictException
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.flag.models import Flag
from fedlearner_webconsole.rpc.v2.resource_service_client import ResourceServiceClient

file_manager = FileManager()
file_operator = FileOperator()


class UploadAlgorithmFile(Schema):
    path = fields.Str(required=True)
    filename = fields.Str(required=True)
    is_directory = fields.Boolean(required=False, load_default=False)
    file = fields.Raw(required=False, type='file', load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        return data


def _validate_parameter(parameter):
    try:
        ParseDict(json.loads(parameter), AlgorithmParameter())
    except:  # pylint: disable=bare-except
        return False
    return True


class CreateAlgorithmProjectParams(Schema):
    name = fields.Str(required=True)
    type = fields.Str(required=True, validate=validate.OneOf([a.name for a in AlgorithmType]))
    parameter = fields.Str(required=False, load_default='{}', validate=_validate_parameter)
    comment = fields.Str(required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        data['parameter'] = ParseDict(json.loads(data['parameter']), AlgorithmParameter())
        return data


class GetAlgorithmProjectParams(Schema):
    name = fields.Str(required=False, load_default=None)
    sources = fields.List(fields.Str(required=False,
                                     load_default=None,
                                     validate=validate.OneOf(
                                         [Source.PRESET.name, Source.USER.name, Source.THIRD_PARTY.name])),
                          load_default=None)
    type = fields.Str(required=False, load_default=None, validate=validate.OneOf([a.name for a in AlgorithmType]))
    keyword = fields.Str(required=False, load_default=None)
    page = fields.Integer(required=False, load_default=None)
    page_size = fields.Integer(required=False, load_default=None)
    filter_exp = FilterExpField(data_key='filter', required=False, load_default=None)
    sorter_exp = fields.String(data_key='order_by', required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        return data


class PatchAlgorithmProjectParams(Schema):
    parameter = fields.Dict(required=False, load_default=None)
    comment = fields.Str(required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        return data


def _get_project(project_id: int, session: Session) -> Project:
    project = session.query(Project).get(project_id)
    if project is None:
        raise NotFoundException(f'project {project_id} is not found')
    return project


def _get_participant(participant_id: int, session: Session) -> Participant:
    participant = session.query(Participant).get(participant_id)
    if participant is None:
        raise NotFoundException(f'participant {participant_id} is not found')
    return participant


def _get_algorithm(algo_id: int, session: Session, project_id: Optional[int] = None) -> Algorithm:
    if project_id:
        algo = session.query(Algorithm).filter_by(id=algo_id, project_id=project_id).first()
    else:
        algo = session.query(Algorithm).get(algo_id)
    if algo is None:
        raise NotFoundException(f'algorithm {algo_id} is not found')
    return algo


def _get_algorithm_project(algo_project_id: int,
                           session: Session,
                           project_id: Optional[int] = None) -> AlgorithmProject:
    if project_id:
        algo_project = session.query(AlgorithmProject).filter_by(id=algo_project_id, project_id=project_id).first()
    else:
        algo_project = session.query(AlgorithmProject).get(algo_project_id)
    if algo_project is None:
        raise NotFoundException(f'algorithm project {algo_project_id} is not found')
    return algo_project


def _get_pending_algorithm(pending_algorithm_id: int, session: Session) -> PendingAlgorithm:
    pending_algo = session.query(PendingAlgorithm).get(pending_algorithm_id)
    if pending_algo is None:
        raise NotFoundException(f'pending algorithm {pending_algorithm_id} is not found')
    return pending_algo


class AlgorithmApi(Resource):

    @credentials_required
    @use_kwargs({'download': fields.Bool(required=False, load_default=False)}, location='query')
    def get(self, download: Optional[bool], algo_id: int):
        """Get the algorithm by id
        ---
        tags:
          - algorithm
        description: get the algorithm by id
        parameters:
        - in: path
          name: algo_id
          schema:
            type: integer
        - in: query
          name: download
          schema:
            type: boolean
        responses:
          200:
            description: detail of the algorithm
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmPb'
        """
        with db.session_scope() as session:
            algo = _get_algorithm(algo_id, session)
            # TODO(gezhengqiang): split download out for swagger
            if not download:
                return make_flask_response(algo.to_proto())
            files = file_manager.ls(algo.path, include_directory=True)
            if len(files) == 0:
                return make_flask_response(status=HTTPStatus.NO_CONTENT)
            with tempfile.NamedTemporaryFile(suffix='.tar') as temp_file:
                file_operator.archive_to([file.path for file in files], temp_file.name)
                target_file_name = os.path.join(os.path.dirname(temp_file.name), f'{algo.name}.tar')
                file_manager.copy(temp_file.name, target_file_name)
                return send_file(filename_or_fp=target_file_name, mimetype='application/x-tar', as_attachment=True)

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.ALGORITHM, op_type=Event.OperationType.DELETE)
    def delete(self, algo_id: int):
        """Delete the model
        ---
        tags:
          - algorithm
        description: delete the model
        parameters:
        - in: path
          name: algo_id
          schema:
            type: integer
        responses:
          204:
            description: delete the model successfully
        """
        with db.session_scope() as session:
            algo = _get_algorithm(algo_id, session)
            AlgorithmService(session).delete(algo)
            session.commit()
        return make_flask_response(status=HTTPStatus.NO_CONTENT)

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.ALGORITHM, op_type=Event.OperationType.UPDATE)
    @use_kwargs({'comment': fields.Str(required=False, load_default=None)}, location='json')
    def patch(self, comment: Optional[str], algo_id: int):
        """Update an algorithm
        ---
        tags:
          - algorithm
        description: update an algorithm
        parameters:
        - in: path
          name: algo_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  comment:
                    type: string
        responses:
          200:
            description: detail of the algorithm
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmPb'
        """
        with db.session_scope() as session:
            algo = _get_algorithm(algo_id, session)
            if comment:
                algo.comment = comment
            session.commit()
            return make_flask_response(algo.to_proto())


class AlgorithmsApi(Resource):

    @credentials_required
    @use_kwargs({'algo_project_id': fields.Integer(required=False, load_default=None)}, location='query')
    def get(self, project_id: int, algo_project_id: Optional[int]):
        """Get the algorithms by algo_project_id
        ---
        tags:
          - algorithm
        description: get the algorithms by algo_project_id
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: query
          name: algo_project_id
          schema:
            type: integer
        responses:
          200:
            description: detail of the algorithms
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmPb'
        """
        with db.session_scope() as session:
            query = session.query(Algorithm)
            if project_id:  # It means not to filter projects when project_id is 0
                query = query.filter_by(project_id=project_id)
            if algo_project_id:
                query = query.filter_by(algorithm_project_id=algo_project_id)
            query = query.order_by(Algorithm.created_at.desc())
            algos = query.all()
            results = [algo.to_proto() for algo in algos]
        return make_flask_response(results)


class AlgorithmTreeApi(Resource):

    @credentials_required
    def get(self, algo_id: int):
        """Get the algorithm tree
        ---
        tags:
          - algorithm
        description: get the algorithm tree
        parameters:
        - in: path
          name: algo_id
          schema:
            type: integer
        responses:
          200:
            description: the file tree of the algorithm
            content:
              application/json:
                schema:
                  type: array
                  items:
                    name: FileTreeNode
                    type: object
                    properties:
                      filename:
                        type: string
                      path:
                        type: string
                      size:
                        type: integer
                      mtime:
                        type: integer
                      is_directory:
                        type: boolean
                      files:
                        type: array
                        items:
                          type: object
                          description: FileTreeNode
        """
        with db.session_scope() as session:
            algo = _get_algorithm(algo_id, session)
            # relative path is used in returned file tree
            file_trees = FileTreeBuilder(algo.path, relpath=True).build()
            return make_flask_response(file_trees)


class AlgorithmFilesApi(Resource):

    @credentials_required
    @use_kwargs({'path': fields.Str(required=True)}, location='query')
    def get(self, path: str, algo_id: int):
        """Get the algorithm file
        ---
        tags:
          - algorithm
        description: get the algorithm file
        parameters:
        - in: path
          name: algo_id
          schema:
            type: integer
        - in: query
          name: path
          schema:
            type: string
        responses:
          200:
            description: content and path of the algorithm file
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    content:
                      type: string
                    path:
                      type: string
          400:
            description: error exists when reading the file
          401:
            description: unauthorized path under the algorithm
        """
        with db.session_scope() as session:
            algo = _get_algorithm(algo_id, session)
            path = normalize_path(os.path.join(algo.path, path))
        if not algo.is_path_accessible(path):
            raise UnauthorizedException(f'Unauthorized path {path} under algorithm {algo_id}')
        try:
            text = file_manager.read(path)
        except Exception as e:
            raise InvalidArgumentException(details=str(e)) from e
        relpath = os.path.relpath(path, algo.path)
        return make_flask_response({'content': text, 'path': relpath})


def _build_release_status_query(exp: SimpleExpression) -> ColumnElement:
    col: Column = getattr(AlgorithmProject, '_release_status')
    return col.in_(exp.list_value.string_list)


class AlgorithmProjectsApi(Resource):

    FILTER_FIELDS = {
        'name': SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: None}),
        'release_status': SupportedField(type=FieldType.STRING, ops={FilterOp.IN: _build_release_status_query}),
        'type': SupportedField(type=FieldType.STRING, ops={FilterOp.IN: None}),
    }

    SORTER_FIELDS = ['created_at', 'updated_at']

    def __init__(self):
        self._filter_builder = FilterBuilder(model_class=AlgorithmProject, supported_fields=self.FILTER_FIELDS)
        self._sorter_builder = SorterBuilder(model_class=AlgorithmProject, supported_fields=self.SORTER_FIELDS)

    @credentials_required
    @use_args(GetAlgorithmProjectParams(), location='query')
    def get(self, params: dict, project_id: int):
        """Get the list of the algorithm project
        ---
        tags:
          - algorithm
        description: get the list of the algorithm project
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: query
          name: name
          schema:
            type: string
        - in: query
          name: sources
          schema:
            type: array
            items:
              type: string
        - in: query
          name: type
          schema:
            type: string
        - in: query
          name: keyword
          schema:
            type: string
        - in: query
          name: page
          schema:
            type: integer
        - in: query
          name: page_size
          schema:
            type: integer
        - in: query
          name: filter
          schema:
            type: string
        - in: query
          name: order_by
          schema:
            type: string
        responses:
          200:
            description: list of the algorithm projects
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmProjectPb'
        """
        with db.session_scope() as session:
            query = session.query(AlgorithmProject)
            if params['name']:
                query = query.filter_by(name=params['name'])
            if project_id:
                query = query.filter_by(project_id=project_id)
            if params['type']:
                query = query.filter_by(type=AlgorithmType[params['type']])
            if params['sources']:
                sources = [Source[n] for n in params['sources']]
                query = query.filter(AlgorithmProject.source.in_(sources))
            if params['keyword']:
                query = query.filter(AlgorithmProject.name.like(f'%{params["keyword"]}%'))
            if params['filter_exp']:
                try:
                    query = self._filter_builder.build_query(query, params['filter_exp'])
                except ValueError as e:
                    raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            try:
                if params['sorter_exp'] is not None:
                    sorter_exp = parse_expression(params['sorter_exp'])
                else:
                    sorter_exp = SortExpression(field='created_at', is_asc=False)
                query = self._sorter_builder.build_query(query, sorter_exp)
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid sorted: {str(e)}') from e
            pagination = paginate(query, params['page'], params['page_size'])
            data = [d.to_proto() for d in pagination.get_items()]
            return make_flask_response(data=data, page_meta=pagination.get_metadata())

    @input_validator
    @credentials_required
    @use_args(CreateAlgorithmProjectParams(), location='form')
    @emits_event(resource_type=Event.ResourceType.ALGORITHM_PROJECT, op_type=Event.OperationType.CREATE)
    def post(self, param: dict, project_id: int):
        """Create an algorithm project
        ---
        tags:
          - algorithm
        description: create an algorithm project
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/CreateAlgorithmProjectParams'
        responses:
          201:
            description: detail of the algorithm project
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmProjectPb'
          400:
            description: the project does not exist
          403:
            description: the algorithm project is forbidden to create
          409:
            description: the algorithm project already exists
        """
        # TODO(hangweiqiang): clear the file if error in subsequent operation
        if not Flag.TRUSTED_COMPUTING_ENABLED.value and param['type'] == AlgorithmType.TRUSTED_COMPUTING.name:
            raise NoAccessException(message='trusted computing is not enabled')
        file = None
        if 'file' in request.files:
            file = request.files['file']
        user = get_current_user()
        path = algorithm_project_path(Envs.STORAGE_ROOT, param['name'])
        with db.session_scope() as session, check_algorithm_file(path):
            project = session.query(Project).get(project_id)
            if project is None:
                raise InvalidArgumentException(details=f'project {project_id} not exist')
            algo_project = session.query(AlgorithmProject).filter_by(name=param['name'],
                                                                     source=Source.USER,
                                                                     project_id=project_id).first()
            if algo_project is not None:
                raise ResourceConflictException(message=f'algorithm project {param["name"]} already exists')
            file_manager.mkdir(path)
            algo_project = AlgorithmProjectService(session).create_algorithm_project(
                name=param['name'],
                project_id=project_id,
                algorithm_type=AlgorithmType[param['type']],
                username=user.username,
                parameter=param['parameter'],
                comment=param['comment'],
                file=file,
                path=path)
            session.commit()
            return make_flask_response(algo_project.to_proto(), status=HTTPStatus.CREATED)


class AlgorithmProjectApi(Resource):

    @credentials_required
    def get(self, algo_project_id: int):
        """Get the algorithm project by id
        ---
        tags:
          - algorithm
        description: get the algorithm project by id
        parameters:
        - in: path
          name: algo_project_id
          schema:
            type: integer
        responses:
          200:
            description: detail of the algorithm project
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmProjectPb'
        """
        with db.session_scope() as session:
            algo_project = _get_algorithm_project(algo_project_id, session)
            result = algo_project.to_proto()
            return make_flask_response(result)

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.ALGORITHM_PROJECT, op_type=Event.OperationType.UPDATE)
    @use_args(PatchAlgorithmProjectParams(), location='json')
    def patch(self, params: dict, algo_project_id: int):
        """Update the algorithm project
        ---
        tags:
          - algorithm
        description: update the algorithm project
        parameters:
        - in: path
          name: algorithm_project_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/PatchAlgorithmProjectParams'
        responses:
          200:
            description: detail of the algorithm project
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmProjectPb'
        """
        with db.session_scope() as session:
            algo_project = _get_algorithm_project(algo_project_id, session)
            if algo_project.source == Source.THIRD_PARTY:
                raise NoAccessException(message='algo_project from THIRD_PARTY can not be edited')
            if params['comment']:
                algo_project.comment = params['comment']
            if params['parameter']:
                parameter = ParseDict(params['parameter'], AlgorithmParameter())
                algo_project.set_parameter(parameter)
                algo_project.release_status = ReleaseStatus.UNRELEASED
            session.commit()
            return make_flask_response(algo_project.to_proto())

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.ALGORITHM_PROJECT, op_type=Event.OperationType.DELETE)
    def delete(self, algo_project_id: int):
        """Delete the algorithm project
        ---
        tags:
          - algorithm
        description: delete the algorithm project
        parameters:
        - in: path
          name: algo_project_id
          schema:
            type: integer
        responses:
          204:
            description: delete the algorithm project successfully
        """
        with db.session_scope() as session:
            algo_project = _get_algorithm_project(algo_project_id, session)
            AlgorithmProjectService(session).delete(algo_project)
            session.commit()
        return make_flask_response(status=HTTPStatus.NO_CONTENT)


class AlgorithmProjectTreeApi(Resource):

    @credentials_required
    def get(self, algo_project_id: int):
        """Get the algorithm project file tree
        ---
        tags:
          - algorithm
        description: get the algorithm project file tree
        parameters:
        - in: path
          name: algo_project_id
          schema:
            type: integer
        responses:
          200:
            description: the file tree of the algorithm project
            content:
              application/json:
                schema:
                  type: array
                  items:
                    name: FileTreeNode
                    type: object
                    properties:
                      filename:
                        type: string
                      path:
                        type: string
                      size:
                        type: integer
                      mtime:
                        type: integer
                      is_directory:
                        type: boolean
                      files:
                        type: array
                        items:
                          type: object
                          description: FileTreeNode
        """
        with db.session_scope() as session:
            algo_project = _get_algorithm_project(algo_project_id, session)
            # relative path is used in returned file tree
            # TODO(gezhengqiang): change to return empty array
            if algo_project.path is None:
                return make_flask_response([])
            file_trees = FileTreeBuilder(algo_project.path, relpath=True).build()
            return make_flask_response(file_trees)


class AlgorithmProjectFilesApi(Resource):

    @staticmethod
    def _mark_algorithm_project_unreleased(algo_project_id: int):
        with db.session_scope() as session:
            algo_project = _get_algorithm_project(algo_project_id, session)
            algo_project.release_status = ReleaseStatus.UNRELEASED
            session.commit()

    @credentials_required
    @use_kwargs({'path': fields.Str(required=True)}, location='query')
    def get(self, path: str, algo_project_id: int):
        """Get the files of the algorithm project
        ---
        tags:
          - algorithm
        description: get the files of the algorithm project
        parameters:
        - in: path
          name: algo_project_id
          schema:
            type: integer
        - in: query
          name: path
          schema:
            type: string
        responses:
          200:
            description: content and path of the algorithm file
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    content:
                      type: string
                    path:
                      type: string
          400:
            description: error exists when reading the file
          401:
            description: unauthorized path under the algorithm
        """
        with db.session_scope() as session:
            algo_project = _get_algorithm_project(algo_project_id, session)
            path = normalize_path(os.path.join(algo_project.path, path))
        if not algo_project.is_path_accessible(path):
            raise UnauthorizedException(f'Unauthorized path {path} under algorithm {algo_project_id}')
        try:
            content = file_manager.read(path)
        except Exception as e:
            raise InvalidArgumentException(details=str(e)) from e
        relpath = os.path.relpath(path, algo_project.path)
        return make_flask_response({'content': content, 'path': relpath})

    @credentials_required
    @use_kwargs({'path': fields.Str(required=True), 'filename': fields.Str(required=True)}, location='form')
    @emits_event(resource_type=Event.ResourceType.ALGORITHM_PROJECT, op_type=Event.OperationType.UPDATE)
    def post(self, path: str, filename: str, algo_project_id: int):
        """Upload the algorithm project file
        ---
        tags:
          - algorithm
        description: upload the algorithm project file
        parameters:
        - in: path
          name: algo_project_id
          schema:
            type: integer
        - in: form
          name: path
          schema:
            type: string
        - in: form
          name: filename
          schema:
            type: string
        responses:
          200:
            description: filename and path of the algorithm project file
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    path:
                      type: string
                    filename:
                      type: string
          400:
            description: file does not exist or is not directory
          401:
            description: unauthorized path under the algorithm project
        """
        with db.session_scope() as session:
            algo_project = _get_algorithm_project(algo_project_id, session)
            # TODO(hangweiqiang): check algorithm file accessibility in decorator
            path = normalize_path(os.path.join(algo_project.path, path))
        if not algo_project.is_path_accessible(path):
            raise UnauthorizedException(f'Unauthorized path {path} under algorithm project {algo_project_id}')
        if not file_manager.isdir(path):
            raise InvalidArgumentException(details=f'file {str(path)} does not exist or is not directory')
        secure_file_name = secure_filename(filename)
        file_path = normalize_path(os.path.join(path, secure_file_name))
        file = request.files['file']
        file_content = file.read()
        file_manager.write(file_path, file_content)
        self._mark_algorithm_project_unreleased(algo_project_id)
        relpath = os.path.relpath(path, algo_project.path)
        return make_flask_response({'path': relpath, 'filename': secure_file_name})

    @credentials_required
    @use_args(UploadAlgorithmFile(), location='form')
    @emits_event(resource_type=Event.ResourceType.ALGORITHM_PROJECT, op_type=Event.OperationType.UPDATE)
    def put(self, param: dict, algo_project_id: int):
        """put the algorithm project file
        ---
        tags:
          - algorithm
        description: put the algorithm project file
        parameters:
        - in: path
          name: algo_project_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/UploadAlgorithmFile'
        responses:
          200:
            description: content, path and filename of the algorithm project
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    content:
                      type: string
                    path:
                      type: string
                    filename:
                      type: string
          400:
            description: file does not exist or is not directory or file path already exists
          401:
            description: unauthorized path under the algorithm project
        """
        with db.session_scope() as session:
            algo_project = _get_algorithm_project(algo_project_id, session)
            path = normalize_path(os.path.join(algo_project.path, param['path']))
        if not algo_project.is_path_accessible(path):
            raise UnauthorizedException(f'Unauthorized path {path} under algorithm project {algo_project_id}')
        if not file_manager.isdir(path):
            raise InvalidArgumentException(details=f'file {str(param["path"])} does not exist or is not directory')
        secure_file_name = secure_filename(param['filename'])
        file_path = os.path.join(path, secure_file_name)
        file_content = None
        if param['is_directory']:
            if file_manager.exists(file_path):
                raise InvalidArgumentException(details=f'file {str(param["path"])} already exists')
            file_manager.mkdir(file_path)
        else:
            file_content = param['file']
            file_manager.write(file_path, file_content or '')
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8')
        self._mark_algorithm_project_unreleased(algo_project_id)
        relpath = os.path.relpath(path, algo_project.path)
        return make_flask_response({'content': file_content, 'path': relpath, 'filename': secure_file_name})

    @credentials_required
    @use_kwargs({'path': fields.Str(required=True)}, location='query')
    @emits_event(resource_type=Event.ResourceType.ALGORITHM_PROJECT, op_type=Event.OperationType.UPDATE)
    def delete(self, path: str, algo_project_id: int):
        """Delete the algorithm project file
        ---
        tags:
          - algorithm
        description: delete the algorithm project file
        parameters:
        - in: path
          name: algo_project_id
          schema:
            type: integer
        - in: query
          name: path
          schema:
            type: string
        responses:
          204:
            description: delete the algorithm project file successfully
          400:
            description: error exists when removing the file
          401:
            description: unauthorized path under the algorithm project
        """
        with db.session_scope() as session:
            algo_project = _get_algorithm_project(algo_project_id, session)
            path = normalize_path(os.path.join(algo_project.path, path))
        if not algo_project.is_path_accessible(path):
            raise UnauthorizedException(f'Unauthorized path {path} under algorithm project {algo_project_id}')
        try:
            file_manager.remove(path)
        except Exception as e:
            raise InvalidArgumentException(details=str(e)) from e
        self._mark_algorithm_project_unreleased(algo_project_id)
        return make_flask_response(status=HTTPStatus.NO_CONTENT)

    @credentials_required
    @use_kwargs({'path': fields.Str(required=True), 'dest': fields.Str(required=True)}, location='json')
    @emits_event(resource_type=Event.ResourceType.ALGORITHM_PROJECT, op_type=Event.OperationType.UPDATE)
    def patch(self, path: str, dest: str, algo_project_id: int):
        """Patch the algorithm project file
        ---
        tags:
          - algorithm
        description: patch the algorithm project file
        parameters:
        - in: path
          name: algo_project_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  path:
                    type: string
                  dest:
                    type: string
        responses:
          204:
            description: patch the algorithm project file successfully
          401:
            description: unauthorized path under the algorithm project
          401:
            description: unauthorized dest under the algorithm project
        """
        with db.session_scope() as session:
            algo_project = _get_algorithm_project(algo_project_id, session)
            path = normalize_path(os.path.join(algo_project.path, path))
            dest = normalize_path(os.path.join(algo_project.path, dest))
        if not algo_project.is_path_accessible(path):
            raise UnauthorizedException(f'Unauthorized path {path} under algorithm project {algo_project_id}')
        if not algo_project.is_path_accessible(dest):
            raise UnauthorizedException(f'Unauthorized dest {dest} under algorithm project {algo_project_id}')
        try:
            file_manager.rename(path, dest)
        except Exception as e:
            raise InvalidArgumentException(details=str(e)) from e
        self._mark_algorithm_project_unreleased(algo_project_id)
        return make_flask_response(status=HTTPStatus.NO_CONTENT)


class ParticipantAlgorithmProjectsApi(Resource):

    @credentials_required
    @use_kwargs(
        {
            'filter_exp': FilterExpField(data_key='filter', required=False, load_default=None),
            'sorter_exp': fields.String(data_key='order_by', required=False, load_default=None)
        },
        location='query')
    def get(self, project_id: int, participant_id: int, filter_exp: Optional[str], sorter_exp: Optional[str]):
        """Get the list of the participant algorithm project
        ---
        tags:
          - algorithm
        description: get the list of the participant algorithm project
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: participant_id
          schema:
            type: integer
        - in: query
          name: filter_exp
          schema:
            type: string
        - in: query
          name: sorter_exp
          schema:
            type: string
        responses:
          200:
            description: list of the participant algorithm projects
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmProjectPb'
        """
        with db.session_scope() as session:
            project = _get_project(project_id, session)
            participants = project.participants
            if participant_id:
                participants = [_get_participant(participant_id, session)]
        algorithm_projects = []
        for participant in participants:
            try:
                client = ResourceServiceClient.from_project_and_participant(participant.domain_name, project.name)
                participant_algorithm_projects = client.list_algorithm_projects(
                    filter_exp=filter_exp).algorithm_projects
                for algo_project in participant_algorithm_projects:
                    algo_project.participant_id = participant.id
                algorithm_projects.extend(participant_algorithm_projects)
            except grpc.RpcError as e:
                logging.warning(f'[algorithm] failed to get {participant.type} participant {participant.id}\'s '
                                f'algorithm projects with grpc code {e.code()} and details {e.details()}')
        if len(algorithm_projects) != 0:
            field = 'created_at'
            is_asc = False
            if sorter_exp:
                sorter_exp = parse_expression(sorter_exp)
                field = sorter_exp.field
                is_asc = sorter_exp.is_asc
            try:
                algorithm_projects = sorted(algorithm_projects, key=lambda x: getattr(x, field), reverse=not is_asc)
            except AttributeError as e:
                raise InvalidArgumentException(details=f'Invalid sort attribute: {str(e)}') from e
        return make_flask_response(algorithm_projects)


class ParticipantAlgorithmProjectApi(Resource):

    def get(self, project_id: int, participant_id: int, algorithm_project_uuid: str):
        """Get the participant algorithm project by algorithm_project_uuid
        ---
        tags:
          - algorithm
        description: get the participant algorithm project by algorithm_project_uuid
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: participant_id
          schema:
            type: integer
        - in: path
          name: algorithm_project_uuid
          schema:
            type: string
        responses:
          200:
            description: detail of the participant algorithm project
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmProjectPb'

        """
        with db.session_scope() as session:
            project = _get_project(project_id, session)
            participant = _get_participant(participant_id, session)
        client = ResourceServiceClient.from_project_and_participant(participant.domain_name, project.name)
        algorithm_project = client.get_algorithm_project(algorithm_project_uuid=algorithm_project_uuid)
        return make_flask_response(algorithm_project)


class ParticipantAlgorithmsApi(Resource):

    @credentials_required
    @use_kwargs({'algorithm_project_uuid': fields.Str(required=True)}, location='query')
    def get(self, project_id: int, participant_id: int, algorithm_project_uuid: str):
        """Get the participant algorithms by algorithm_project_uuid
        ---
        tags:
          - algorithm
        description: get the participant algorithms by algorithm_project_uuid
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: participant_id
          schema:
            type: integer
        - in: query
          name: algorithm_project_uuid
          schema:
            type: string
        responses:
          200:
            description: list of the participant algorithms
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmPb'
        """
        with db.session_scope() as session:
            project = _get_project(project_id, session)
            participant = _get_participant(participant_id, session)
        client = ResourceServiceClient.from_project_and_participant(participant.domain_name, project.name)
        participant_algorithms = client.list_algorithms(algorithm_project_uuid).algorithms
        for algo in participant_algorithms:
            algo.participant_id = participant_id
        algorithms = sorted(participant_algorithms, key=lambda x: x.created_at, reverse=True)
        return make_flask_response(algorithms)


class ParticipantAlgorithmApi(Resource):

    @credentials_required
    def get(self, project_id: int, participant_id: int, algorithm_uuid: str):
        """Get the participant algorithm by algorithm_uuid
        ---
        tags:
          - algorithm
        description: get the participant algorithm by algorithm_uuid
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: participant_id
          schema:
            type: integer
        - in: path
          name: algorithm_uuid
          schema:
            type: string
        responses:
          200:
            description: detail of the participant algorithm
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmPb'

        """
        with db.session_scope() as session:
            project = _get_project(project_id, session)
            participant = _get_participant(participant_id, session)
        client = ResourceServiceClient.from_project_and_participant(participant.domain_name, project.name)
        algorithm = client.get_algorithm(algorithm_uuid)
        return make_flask_response(algorithm)


class ParticipantAlgorithmTreeApi(Resource):

    @credentials_required
    def get(self, project_id: int, participant_id: int, algorithm_uuid: str):
        """Get the participant algorithm tree
        ---
        tags:
          - algorithm
        description: get the participant algorithm tree
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: participant_id
          schema:
            type: integer
        - in: path
          name: algorithm_uuid
          schema:
            type: string
        responses:
          200:
            description: the file tree of the participant algorithm
            content:
              application/json:
                schema:
                  type: array
                  items:
                    name: FileTreeNode
                    type: object
                    properties:
                      filename:
                        type: string
                      path:
                        type: string
                      size:
                        type: integer
                      mtime:
                        type: integer
                      is_directory:
                        type: boolean
                      files:
                        type: array
                        items:
                          type: object
                          description: FileTreeNode
        """
        algorithm = AlgorithmFetcher(project_id=project_id).get_algorithm_from_participant(
            algorithm_uuid=algorithm_uuid, participant_id=participant_id)

        # relative path is used in returned file tree
        file_trees = FileTreeBuilder(algorithm.path, relpath=True).build()
        return make_flask_response(file_trees)


class ParticipantAlgorithmFilesApi(Resource):

    @credentials_required
    @use_kwargs({'path': fields.Str(required=True)}, location='query')
    def get(self, project_id: int, participant_id: int, algorithm_uuid: str, path: str):
        """Get the algorithm file
        ---
        tags:
          - algorithm
        description: get the algorithm file
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: participant_id
          schema:
            type: integer
        - in: path
          name: algorithm_uuid
          schema:
            type: string
        - in: query
          name: path
          schema:
            type: string
        responses:
          200:
            description: content and path of the participant algorithm file
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    content:
                      type: string
                    path:
                      type: string
          400:
            description: error exists when reading the file
          401:
            description: unauthorized path under the algorithm
        """
        algorithm = AlgorithmFetcher(project_id=project_id).get_algorithm_from_participant(
            algorithm_uuid=algorithm_uuid, participant_id=participant_id)
        path = normalize_path(os.path.join(algorithm.path, path))
        if not normalize_path(path).startswith(algorithm.path):
            raise UnauthorizedException(f'Unauthorized path {path} under the participant algorithm {algorithm_uuid}')
        try:
            text = file_manager.read(path)
        except Exception as e:
            raise InvalidArgumentException(details=str(e)) from e
        relpath = os.path.relpath(path, algorithm.path)
        return make_flask_response({'content': text, 'path': relpath})


class FetchAlgorithmApi(Resource):

    @credentials_required
    def get(self, project_id: int, algorithm_uuid: str):
        """Get the algorithm by uuid
        ---
        tags:
          - algorithm
        description: get the algorithm by uuid, whether it is from your own side or from a participant
        parameters:
        - in: path
          name: algo_id
          schema:
            type: integer
        - in: path
          name: algorithm_uuid
          schema:
            type: string
        responses:
          200:
            description: detail of the algorithm
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmPb'
        """
        algorithm = AlgorithmFetcher(project_id=project_id).get_algorithm(uuid=algorithm_uuid)
        return make_flask_response(algorithm)


class UpdatePresetAlgorithmApi(Resource):

    @credentials_required
    @admin_required
    @emits_event(resource_type=Event.ResourceType.PRESET_ALGORITHM, op_type=Event.OperationType.UPDATE)
    def post(self):
        """Update the preset algorithm
        ---
        tags:
          - algorithm
        description: update the preset algorithm
        responses:
          200:
            description: detail of the preset algorithm projects
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmProjectPb'
        """
        create_algorithm_if_not_exists()
        with db.session_scope() as session:
            algo_projects = session.query(AlgorithmProject).filter_by(source=Source.PRESET).all()
            results = [project.to_proto() for project in algo_projects]
        return make_flask_response(results)


class ReleaseAlgorithmApi(Resource):

    @input_validator
    @credentials_required
    @use_kwargs({'comment': fields.Str(required=False, load_default=None, location='body')})
    @emits_event(resource_type=Event.ResourceType.ALGORITHM, op_type=Event.OperationType.CREATE)
    def post(self, comment: Optional[str], algo_project_id: int):
        """Release the algorithm
        ---
        tags:
          - algorithm
        description: release the algorithm
        parameters:
        - in: path
          name: algo_project_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  comment:
                    type: string
        responses:
          200:
            description: detail of the algorithm
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmPb'
        """
        user = get_current_user()
        with db.session_scope() as session:
            algorithm_project = _get_algorithm_project(algo_project_id, session)
            if algorithm_project.source == Source.THIRD_PARTY:
                raise NoAccessException(message='algo_project from THIRD_PARTY can not be released')
            version = algorithm_project.latest_version + 1
            path = algorithm_path(Envs.STORAGE_ROOT, algorithm_project.name, version)
            with check_algorithm_file(path):
                algo = AlgorithmProjectService(session).release_algorithm(algorithm_project=algorithm_project,
                                                                          username=user.username,
                                                                          comment=comment,
                                                                          path=path)
                session.commit()
                return make_flask_response(algo.to_proto())


class PublishAlgorithmApi(Resource):

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.ALGORITHM, op_type=Event.OperationType.UPDATE)
    def post(self, algorithm_id: int, project_id: int):
        """Publish the algorithm
        ---
        tags:
          - algorithm
        description: publish the algorithm
        parameters:
        - in: path
          name: algorithm_id
          schema:
            type: integer
        - in: path
          name: project_id
          schema:
            type: integer
        responses:
          200:
            description: detail of the algorithm
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmPb'
        """
        with db.session_scope() as session:
            _get_algorithm(algorithm_id, session, project_id)
            algorithm = AlgorithmService(session).publish_algorithm(algorithm_id, project_id)
            session.commit()
            return make_flask_response(algorithm.to_proto())


class UnpublishAlgorithmApi(Resource):

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.ALGORITHM, op_type=Event.OperationType.UPDATE)
    def post(self, algorithm_id: int, project_id: int):
        """Unpublish the algorithm
        ---
        tags:
          - algorithm
        description: unpublish the algorithm
        parameters:
        - in: path
          name: algorithm_id
          schema:
            type: integer
        - in: path
          name: project_id
          schema:
            type: integer
        responses:
          200:
            description: detail of the algorithm
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.AlgorithmPb'
        """
        with db.session_scope() as session:
            _get_algorithm(algorithm_id, session, project_id)
            algorithm = AlgorithmService(session).unpublish_algorithm(algorithm_id, project_id)
            session.commit()
            return make_flask_response(algorithm.to_proto())


class PendingAlgorithmsApi(Resource):

    @credentials_required
    def get(self, project_id: int):
        """Get the list of the pending algorithms
        ---
        tags:
          - algorithm
        description: get the list of the pending algorithms
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        responses:
          200:
            description: list of the pending algorithms
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.PendingAlgorithmPb'
        """
        with db.session_scope() as session:
            query = session.query(PendingAlgorithm)
            if project_id:
                query = query.filter_by(project_id=project_id)
            query = query.order_by(PendingAlgorithm.created_at.desc())
            pending_algorithms = query.all()
            results = [algo.to_proto() for algo in pending_algorithms]
            return make_flask_response(results)


class AcceptPendingAlgorithmApi(Resource):

    @input_validator
    @credentials_required
    @use_kwargs({
        'name': fields.Str(required=True),
        'comment': fields.Str(required=False, load_default=None, location='body')
    })
    @emits_event(resource_type=Event.ResourceType.ALGORITHM_PROJECT, op_type=Event.OperationType.CREATE)
    def post(self, name: str, comment: Optional[str], project_id: int, pending_algorithm_id: int):
        """Accept the pending algorithm
        ---
        tags:
          - algorithm
        description: accept the pending algorithm
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: pending_algorithm_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                  comment:
                    type: string
        responses:
          204:
            description: accept the pending algorithm successfully
        """
        del project_id
        with db.session_scope() as session:
            pending_algo = _get_pending_algorithm(pending_algorithm_id, session)
            algo_project = session.query(AlgorithmProject).filter_by(
                uuid=pending_algo.algorithm_project_uuid).filter_by(source=Source.THIRD_PARTY).first()
            user = get_current_user()
            if algo_project is None:
                algo_project = PendingAlgorithmService(session).create_algorithm_project(pending_algorithm=pending_algo,
                                                                                         username=user.username,
                                                                                         name=name,
                                                                                         comment=comment)
                session.flush()
            algo_path = algorithm_path(Envs.STORAGE_ROOT, name, pending_algo.version)
            with check_algorithm_file(algo_path):
                pending_algo.deleted_at = now()
                PendingAlgorithmService(session).create_algorithm(pending_algorithm=pending_algo,
                                                                  algorithm_project_id=algo_project.id,
                                                                  username=user.username,
                                                                  path=algo_path,
                                                                  comment=comment)
                algo_project.latest_version = pending_algo.version
                session.commit()
            return make_flask_response(status=HTTPStatus.NO_CONTENT)


class PendingAlgorithmTreeApi(Resource):

    @credentials_required
    def get(self, project_id: int, pending_algo_id: int):
        """Get the file tree of the pending algorithm
        ---
        tags:
          - algorithm
        description: get the file tree of the pending algorithm
        parameters:
        - in: path
          name: pending_algo_id
          schema:
            type: integer
        - in: path
          name: project_id
          schema:
            type: integer
        responses:
          200:
            description: the file tree of the pending algorithm
            content:
              application/json:
                schema:
                  type: array
                  items:
                    name: FileTreeNode
                    type: object
                    properties:
                      filename:
                        type: string
                      path:
                        type: string
                      size:
                        type: integer
                      mtime:
                        type: integer
                      is_directory:
                        type: boolean
                      files:
                        type: array
                        items:
                          type: object
                          description: FileTreeNode
        """
        with db.session_scope() as session:
            pending_algo = _get_pending_algorithm(pending_algo_id, session)
            # relative path is used in returned file tree
            file_trees = FileTreeBuilder(pending_algo.path, relpath=True).build()
            return make_flask_response(file_trees)


class PendingAlgorithmFilesApi(Resource):

    @credentials_required
    @use_kwargs({'path': fields.Str(required=True)}, location='query')
    def get(self, path: str, project_id: int, pending_algo_id: int):
        """Get the files of the pending algorithm
        ---
        tags:
          - algorithm
        description: get the files of the pending algorithm
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: pending_algo_id
          schema:
            type: integer
        - in: query
          name: path
          schema:
            type: string
        responses:
          200:
            description: content and path of the pending algorithm file
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    content:
                      type: string
                    path:
                      type: string
          400:
            description: error exists when reading the file
          401:
            description: unauthorized path under the pending algorithm
        """
        with db.session_scope() as session:
            pending_algo = _get_pending_algorithm(pending_algo_id, session)
            path = normalize_path(os.path.join(pending_algo.path, path))
        if not pending_algo.is_path_accessible(path):
            raise UnauthorizedException(f'Unauthorized path {path} under pending algorithm {pending_algo_id}')
        try:
            text = file_manager.read(path)
        except Exception as e:
            raise InvalidArgumentException(details=str(e)) from e
        relpath = os.path.relpath(path, pending_algo.path)
        return make_flask_response({'content': text, 'path': relpath})


def initialize_algorithm_apis(api):
    # TODO(gezhengqiang): add project in the url
    api.add_resource(AlgorithmApi, '/algorithms/<int:algo_id>')
    api.add_resource(AlgorithmsApi, '/projects/<int:project_id>/algorithms')
    api.add_resource(AlgorithmTreeApi, '/algorithms/<int:algo_id>/tree')
    api.add_resource(AlgorithmFilesApi, '/algorithms/<int:algo_id>/files')
    api.add_resource(AlgorithmProjectsApi, '/projects/<int:project_id>/algorithm_projects')
    api.add_resource(AlgorithmProjectApi, '/algorithm_projects/<int:algo_project_id>')
    api.add_resource(AlgorithmProjectTreeApi, '/algorithm_projects/<int:algo_project_id>/tree')
    api.add_resource(AlgorithmProjectFilesApi, '/algorithm_projects/<int:algo_project_id>/files')
    api.add_resource(ParticipantAlgorithmProjectsApi,
                     '/projects/<int:project_id>/participants/<int:participant_id>/algorithm_projects')
    api.add_resource(
        ParticipantAlgorithmProjectApi, '/projects/<int:project_id>/participants/<int:participant_id>/'
        'algorithm_projects/<string:algorithm_project_uuid>')
    api.add_resource(ParticipantAlgorithmsApi,
                     '/projects/<int:project_id>/participants/<int:participant_id>/algorithms')
    api.add_resource(ParticipantAlgorithmApi,
                     '/projects/<int:project_id>/participants/<int:participant_id>/algorithms/<string:algorithm_uuid>')
    api.add_resource(
        ParticipantAlgorithmTreeApi,
        '/projects/<int:project_id>/participants/<int:participant_id>/algorithms/<string:algorithm_uuid>/tree')
    api.add_resource(
        ParticipantAlgorithmFilesApi,
        '/projects/<int:project_id>/participants/<int:participant_id>/algorithms/<string:algorithm_uuid>/files')
    api.add_resource(FetchAlgorithmApi, '/projects/<int:project_id>/algorithms/<string:algorithm_uuid>')
    # TODO(gezhengqiang): algorithm project publish has been changed to release, the api will be deleted in future
    api.add_resource(ReleaseAlgorithmApi,
                     '/algorithm_projects/<int:algo_project_id>:publish',
                     endpoint='algorithm_project:publish')
    api.add_resource(ReleaseAlgorithmApi,
                     '/algorithm_projects/<int:algo_project_id>:release',
                     endpoint='algorithm_project:release')
    api.add_resource(PublishAlgorithmApi, '/projects/<int:project_id>/algorithms/<int:algorithm_id>:publish')
    api.add_resource(UnpublishAlgorithmApi, '/projects/<int:project_id>/algorithms/<int:algorithm_id>:unpublish')
    api.add_resource(PendingAlgorithmsApi, '/projects/<int:project_id>/pending_algorithms')
    api.add_resource(AcceptPendingAlgorithmApi,
                     '/projects/<int:project_id>/pending_algorithms/<int:pending_algorithm_id>:accept')
    api.add_resource(PendingAlgorithmTreeApi,
                     '/projects/<int:project_id>/pending_algorithms/<int:pending_algo_id>/tree')
    api.add_resource(PendingAlgorithmFilesApi,
                     '/projects/<int:project_id>/pending_algorithms/<int:pending_algo_id>/files')
    api.add_resource(UpdatePresetAlgorithmApi, '/preset_algorithms:update')
    schema_manager.append(UploadAlgorithmFile)
    schema_manager.append(CreateAlgorithmProjectParams)
    schema_manager.append(GetAlgorithmProjectParams)
    schema_manager.append(PatchAlgorithmProjectParams)

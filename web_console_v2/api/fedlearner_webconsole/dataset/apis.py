# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
# pylint: disable=raise-missing-from
import os

from datetime import datetime, timezone
from http import HTTPStatus

from flask import current_app, request
from flask_restful import Resource, Api, reqparse
from slugify import slugify

from fedlearner_webconsole.dataset.models import (Dataset, DatasetType,
                                                  BatchState, DataBatch)
from fedlearner_webconsole.dataset.services import DatasetService
from fedlearner_webconsole.exceptions import (InvalidArgumentException,
                                              NotFoundException)
from fedlearner_webconsole.db import db_handler as db
from fedlearner_webconsole.proto import dataset_pb2
from fedlearner_webconsole.scheduler.scheduler import scheduler
from fedlearner_webconsole.utils.decorators import jwt_required
from fedlearner_webconsole.utils.file_manager import FileManager

_FORMAT_ERROR_MESSAGE = '{} is empty'


def _get_dataset_path(dataset_name):
    root_dir = current_app.config.get('STORAGE_ROOT')
    prefix = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Builds a path for dataset according to the dataset name
    # Example: '/data/dataset/20210305_173312_test-dataset
    return f'{root_dir}/dataset/{prefix}_{slugify(dataset_name)[:32]}'


class DatasetApi(Resource):
    @jwt_required()
    def get(self, dataset_id):
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(dataset_id)
            if dataset is None:
                raise NotFoundException(
                    f'Failed to find dataset: {dataset_id}')
            return {'data': dataset.to_dict()}

    @jwt_required()
    def patch(self, dataset_id: int):
        parser = reqparse.RequestParser()
        parser.add_argument('name',
                            type=str,
                            required=False,
                            help='dataset name')
        parser.add_argument('comment',
                            type=str,
                            required=False,
                            help='dataset comment')
        parser.add_argument('comment')
        data = parser.parse_args()
        with db.session_scope() as session:
            dataset = session.query(Dataset).filter_by(id=dataset_id).first()
            if not dataset:
                raise NotFoundException(
                    f'Failed to find dataset: {dataset_id}')
            if data['name']:
                dataset.name = data['name']
            if data['comment']:
                dataset.comment = data['comment']
            session.commit()
            return {'data': dataset.to_dict()}, HTTPStatus.OK


class DatasetPreviewApi(Resource):
    def get(self, dataset_id: int):
        if dataset_id <= 0:
            raise NotFoundException(f'Failed to find dataset: {dataset_id}')
        with db.session_scope() as session:
            data = DatasetService(session).get_dataset_preview(dataset_id)
            return {'data': data}


class DatasetMetricsApi(Resource):
    def get(self, dataset_id: int):
        if dataset_id <= 0:
            raise NotFoundException(f'Failed to find dataset: {dataset_id}')
        name = request.args.get('name', None)
        if not name:
            raise InvalidArgumentException(f'required params name')
        with db.session_scope() as session:
            data = DatasetService(session).feature_metrics(name, dataset_id)
            return {'data': data}


class DatasetsApi(Resource):
    @jwt_required()
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('project',
                            type=int,
                            required=False,
                            help='project')
        data = parser.parse_args()
        with db.session_scope() as session:
            datasets = DatasetService(session).get_datasets(
                project_id=int(data['project'] or 0))
            return {'data': [d.to_dict() for d in datasets]}

    @jwt_required()
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name',
                            required=True,
                            type=str,
                            help=_FORMAT_ERROR_MESSAGE.format('name'))
        parser.add_argument('dataset_type',
                            required=True,
                            type=DatasetType,
                            help=_FORMAT_ERROR_MESSAGE.format('dataset_type'))
        parser.add_argument('comment', type=str)
        parser.add_argument('project_id',
                            required=True,
                            type=int,
                            help=_FORMAT_ERROR_MESSAGE.format('project_id'))
        body = parser.parse_args()
        name = body.get('name')
        dataset_type = body.get('dataset_type')
        comment = body.get('comment')
        project_id = body.get('project_id')

        with db.session_scope() as session:
            try:
                # Create dataset
                dataset = Dataset(
                    name=name,
                    dataset_type=dataset_type,
                    comment=comment,
                    path=_get_dataset_path(name),
                    project_id=project_id,
                )
                session.add(dataset)
                # TODO: scan cronjob
                session.commit()
                return {'data': dataset.to_dict()}
            except Exception as e:
                session.rollback()
                raise InvalidArgumentException(details=str(e))


class BatchesApi(Resource):
    @jwt_required()
    def post(self, dataset_id: int):
        parser = reqparse.RequestParser()
        parser.add_argument('event_time', type=int)
        parser.add_argument('files',
                            required=True,
                            type=list,
                            location='json',
                            help=_FORMAT_ERROR_MESSAGE.format('files'))
        parser.add_argument('move', type=bool)
        parser.add_argument('comment', type=str)
        body = parser.parse_args()
        event_time = body.get('event_time')
        files = body.get('files')
        move = body.get('move', False)
        comment = body.get('comment')
        with db.session_scope() as session:
            dataset = session.query(Dataset).filter_by(id=dataset_id).first()
            if dataset is None:
                raise NotFoundException(
                    f'Failed to find dataset: {dataset_id}')
            if event_time is None and dataset.type == DatasetType.STREAMING:
                raise InvalidArgumentException(
                    details='data_batch.event_time is empty')
            # TODO: PSI dataset should not allow multi batches

            # Use current timestamp to fill when type is PSI
            event_time = datetime.fromtimestamp(
                event_time or datetime.utcnow().timestamp(), tz=timezone.utc)
            batch_folder_name = event_time.strftime('%Y%m%d_%H%M%S')
            batch_path = f'{dataset.path}/batch/{batch_folder_name}'
            # Create batch
            batch = DataBatch(dataset_id=dataset.id,
                              event_time=event_time,
                              comment=comment,
                              state=BatchState.NEW,
                              move=move,
                              path=batch_path)
            batch_details = dataset_pb2.DataBatch()
            for file_path in files:
                file = batch_details.files.add()
                file.source_path = file_path
                file_name = file_path.split('/')[-1]
                file.destination_path = f'{batch_path}/{file_name}'
            batch.set_details(batch_details)
            session.add(batch)
            session.commit()
            session.refresh(batch)
            scheduler.wakeup(data_batch_ids=[batch.id])
            return {'data': batch.to_dict()}


class FilesApi(Resource):
    def __init__(self):
        self._file_manager = FileManager()

    @jwt_required()
    def get(self):
        # TODO: consider the security factor
        if 'directory' in request.args:
            directory = request.args['directory']
        else:
            directory = os.path.join(current_app.config.get('STORAGE_ROOT'),
                                     'upload')
        files = self._file_manager.ls(directory, recursive=True)
        return {'data': [dict(file._asdict()) for file in files]}


def initialize_dataset_apis(api: Api):
    api.add_resource(DatasetsApi, '/datasets')
    api.add_resource(DatasetApi, '/datasets/<int:dataset_id>')
    api.add_resource(BatchesApi, '/datasets/<int:dataset_id>/batches')
    api.add_resource(DatasetPreviewApi, '/datasets/<int:dataset_id>/preview')
    api.add_resource(DatasetMetricsApi,
                     '/datasets/<int:dataset_id>/feature_metrics')
    api.add_resource(FilesApi, '/files')

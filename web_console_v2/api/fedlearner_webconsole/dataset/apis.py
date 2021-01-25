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
# pylint: disable=raise-missing-from

import datetime

from flask import current_app
from flask_restful import Resource, Api, reqparse

from fedlearner_webconsole.dataset.models import (Dataset, DatasetType,
                                                  BatchState, DataBatch)
from fedlearner_webconsole.exceptions import (InvalidArgumentException,
                                              NotFoundException)
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto import dataset_pb2
from fedlearner_webconsole.scheduler.scheduler import scheduler

_FORMAT_ERROR_MESSAGE = '{} is empty'


class DatasetApi(Resource):
    def get(self, dataset_id):
        dataset = Dataset.query.get(dataset_id)
        if dataset is None:
            raise NotFoundException()
        return {'data': dataset.to_dict()}


class DatasetsApi(Resource):
    def get(self):
        datasets = Dataset.query.all()
        return {'data': [d.to_dict() for d in datasets]}

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True,
                            type=str, help=_FORMAT_ERROR_MESSAGE.format('name'))
        parser.add_argument('dataset_type', required=True,
                            type=DatasetType,
                            help=_FORMAT_ERROR_MESSAGE.format('dataset_type'))
        parser.add_argument('comment', type=str)
        body = parser.parse_args()
        name = body.get('name')
        dataset_type = body.get('dataset_type')
        comment = body.get('comment')

        if Dataset.query.filter_by(name=name).first() is not None:
            raise InvalidArgumentException(
                details='Dataset {} already exists'.format(name))
        try:
            # Create dataset
            dataset = Dataset(
                name=name,
                dataset_type=dataset_type,
                comment=comment)
            db.session.add(dataset)
            # TODO: scan cronjob
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise InvalidArgumentException(details=str(e))
        return {'data': dataset.to_dict()}


class BatchesApi(Resource):
    def post(self, dataset_id: int):
        parser = reqparse.RequestParser()
        parser.add_argument('event_time', type=int)
        parser.add_argument('files', required=True, type=list,
                            location='json',
                            help=_FORMAT_ERROR_MESSAGE.format('files'))
        parser.add_argument('move', type=bool)
        parser.add_argument('comment', type=str)
        body = parser.parse_args()
        event_time = body.get('event_time')
        files = body.get('files')
        move = body.get('move', False)
        comment = body.get('comment')

        dataset = Dataset.query.filter_by(id=dataset_id).first()
        if dataset is None:
            raise NotFoundException()
        if event_time is None and dataset.type == DatasetType.STREAMING:
            raise InvalidArgumentException(
                details='data_batch.event_time is empty')
        # TODO: PSI dataset should not allow multi batches

        # Create batch
        batch = DataBatch(
            dataset_id=dataset.id,
            # Use current timestamp to fill when type is PSI
            event_time=datetime.datetime.fromtimestamp(
                event_time or datetime.datetime.now().timestamp()),
            comment=comment,
            state=BatchState.NEW,
            move=move,
        )
        batch_details = dataset_pb2.DataBatch()
        root_dir = current_app.config.get('STORAGE_ROOT')
        batch_folder_name = batch.event_time.strftime('%Y%m%d%H%M%S')
        for file_path in files:
            file = batch_details.files.add()
            file.source_path = file_path
            file_name = file_path.split('/')[-1]
            file.destination_path = f'{root_dir}/dataset/{dataset.id}' \
                                    f'/batch/{batch_folder_name}/{file_name}'
        batch.set_details(batch_details)
        db.session.add(batch)
        db.session.commit()
        db.session.refresh(batch)
        scheduler.wakeup(data_batch_ids=[batch.id])
        return {'data': batch.to_dict()}


def initialize_dataset_apis(api: Api):
    api.add_resource(DatasetsApi, '/datasets')
    api.add_resource(DatasetApi, '/datasets/<int:dataset_id>')
    api.add_resource(BatchesApi, '/datasets/<int:dataset_id>/batches')

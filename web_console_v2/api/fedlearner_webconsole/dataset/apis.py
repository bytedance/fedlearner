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

from google.protobuf.json_format import ParseDict
from flask_restful import Resource, Api, reqparse

from fedlearner_webconsole.dataset.models import (Dataset, DatasetType,
                                                  BatchState, DataBatch)
from fedlearner_webconsole.exceptions import (InvalidArgumentException,
                                              NotFoundException)
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.dataset_pb2 import DatasetSource

_FORMAT_ERROR_MESSAGE = '{} is empty'


class DatasetsApi(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True,
                            type=str, help=_FORMAT_ERROR_MESSAGE.format('name'))
        parser.add_argument('type', required=True,
                            type=DatasetType,
                            help=_FORMAT_ERROR_MESSAGE.format('type'))
        parser.add_argument('external_storage_path', type=str,
                            help=_FORMAT_ERROR_MESSAGE
                            .format('external_storage_path'))
        parser.add_argument('comment', type=str,
                            help=_FORMAT_ERROR_MESSAGE.format('comment'))
        body = parser.parse_args()
        name = body.get('name')
        dataset_type = body.get('type')
        external_storage_path = body.get('external_storage_path')
        comment = body.get('comment')

        if Dataset.query.filter_by(name=name).first() is not None:
            raise InvalidArgumentException(
                details='Dataset {} already exists'.format(name))
        try:
            # Create dataset
            dataset = Dataset(
                name=name,
                type=dataset_type,
                external_storage_path=external_storage_path,
                comment=comment)
            db.session.add(dataset)
            # TODO: scan cronjob
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise InvalidArgumentException(details=str(e))
        return {'data': dataset}


class BatchesApi(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('dataset_id', type=int, required=True,
                            help=_FORMAT_ERROR_MESSAGE.format('dataset_id'))
        parser.add_argument('event_time',
                            help=_FORMAT_ERROR_MESSAGE.format('event_time'))
        parser.add_argument('files', required=True,
                            help=_FORMAT_ERROR_MESSAGE.format('files'))
        parser.add_argument('move', type=bool,
                            help=_FORMAT_ERROR_MESSAGE.format('move'))
        parser.add_argument('comment', type=str,
                            help=_FORMAT_ERROR_MESSAGE.format('comment'))
        body = parser.parse_args()
        dataset_id = body.get('dataset_id')
        event_time = body.get('event_time')
        files = body.get('files')
        move = body.get('move', False)
        comment = body.get('comment')

        dataset = Dataset.query.filter_by(id=dataset_id).first()
        if dataset is None:
            raise NotFoundException()
        if dataset.external_storage_path:
            raise InvalidArgumentException(
                details='Cannot import into dataset for scanning')
        if event_time is None and dataset.type == DatasetType.STREAMING:
            raise InvalidArgumentException(
                details='data_batch.event_time is empty')

        # Create batch
        batch = DataBatch()
        # Use current timestamp to fill when type is PSI
        batch.event_time = datetime.datetime.fromtimestamp(
            event_time or datetime.datetime.now().timestamp())
        batch.dataset_id = dataset.id
        batch.comment = comment
        batch.state = BatchState.IMPORTING
        batch.num_file = len(files)
        batch.set_source(ParseDict({'files': files}, DatasetSource()))
        # TODO: Call scheduler to import
        db.session.add(batch)
        db.session.commit()
        return batch.to_dict()


def initialize_dataset_apis(api: Api):
    api.add_resource(DatasetsApi, '/datasets')
    api.add_resource(BatchesApi, '/batches')

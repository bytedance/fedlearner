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

import os
import datetime
import concurrent.futures as futures
from typing import Dict

from google.protobuf.json_format import ParseDict
from flask import current_app
from flask_restful import Resource, Api, reqparse

from fedlearner_webconsole.dataset.models import (Dataset, DatasetType,
                                                  BatchState, DataBatch)
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.proto.dataset_pb2 import DatasetSource

FORMAT_ERROR_MESSAGE = 'Format of {} is wrong'


class DatasetApi(Resource):
    def __init__(self):
        self.executor = futures.ThreadPoolExecutor(max_workers=8)
        self.file_manager = FileManager()

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True,
                            type=str, help=FORMAT_ERROR_MESSAGE.format('name'))
        parser.add_argument('type', required=True,
                            type=DatasetType,
                            help=FORMAT_ERROR_MESSAGE.format('type'))
        parser.add_argument('data_batch', type=dict,
                            help=FORMAT_ERROR_MESSAGE.format('data_batch'))
        parser.add_argument('copy', type=bool,
                            help=FORMAT_ERROR_MESSAGE.format('copy'))
        parser.add_argument('external_storage_path', type=str,
                            help=FORMAT_ERROR_MESSAGE.format('scan_path'))
        parser.add_argument('comment', type=str,
                            help=FORMAT_ERROR_MESSAGE.format('comment'))
        body = parser.parse_args()
        name = body.get('name')
        dataset_type = body.get('type')
        data_batch = body.get('data_batch', {})
        copy = body.get('copy', True)
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
            # Generate auto increased id
            db.session.flush()

            if external_storage_path:
                if self._submit_scan_dataset_cronjob(dataset):
                    db.session.commit()
                    return {'data': dataset.to_dic()}
                db.session.rollback()
                raise InvalidArgumentException(
                    details='Cannot create scan conjob')

            if data_batch.get('event_time') is None and \
                dataset_type == DatasetType.STREAMING:
                raise InvalidArgumentException(details='Event time is empty')

            # Create batch
            batch = DataBatch()
            # Use current timestamp to fill when type is PSI
            batch.event_time = datetime.datetime.fromtimestamp(
                data_batch.get('event_time',
                               datetime.datetime.now().timestamp()))
            batch.dataset_id = dataset.id
            batch.comment = data_batch.get('comment')
            batch.state = BatchState.IMPORTING
            batch.file_num = len(data_batch.get('file', []))
            batch.set_source(
                ParseDict({'file': data_batch.get('file', [])},
                          DatasetSource()))
            db.session.add(batch)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise InvalidArgumentException(details=str(e))
        batch_target_path = os.path.join(os.environ['STORAGE_ROOT_PATH'],
                                         'dataset', str(dataset.id))
        if dataset.type == DatasetType.STREAMING:
            batch_target_path = os.path.join(batch_target_path,
                                             str(batch.event_time.timestamp()))
        # Import dataset in background routine
        self.executor.submit(_import_file_routine_fn,
                             # pylint: disable=protected-access
                             current_app._get_current_object(),
                             batch, batch_target_path, copy)
        return {'data': _aggregate_batches(dataset)}

    def _submit_scan_dataset_cronjob(self, dataset: Dataset) -> bool:
        # TODO
        return True


def _import_file_routine_fn(context, batch: DataBatch, batch_target_path: str,
                            copy: bool):
    file_manager = FileManager()
    # Any exception can cause the state of dataset to be failed
    failed_file = batch_target_path
    try:
        if copy:
            import_function = file_manager.copy
        else:
            import_function = file_manager.move
        # Create batch target directory
        if not file_manager.mkdir(batch_target_path):
            raise RuntimeError(
                'Import batch failed: cannot create dictionary for batch')
        # Import files
        for file in batch.get_source().file:
            failed_file = file
            if import_function(
                file,
                os.path.join(batch_target_path, file.split('/')[-1])):
                _success_move_file_routine(context, file_manager,
                                           batch_target_path, batch)
            else:
                _fail_move_file_routine(context, failed_file, 'Cannot move',
                                        batch)
                break
    except Exception as e:
        _fail_move_file_routine(context, failed_file, str(e), batch)
        raise RuntimeError(str(e))


def _success_move_file_routine(context, file_manager: FileManager,
                               batch_target_path: str, batch: DataBatch):
    with context.app_context():
        batch = db.session.query(DataBatch).with_for_update() \
            .filter_by(dataset_id=batch.dataset_id,
                       event_time=batch.event_time).first()
        # If batch still exists
        if batch:
            batch.imported_file_num += 1
            # All batches finish
            if batch.imported_file_num == batch.file_num:
                batch.file_size = sum([file['size'] for file in
                                       file_manager.ls(batch_target_path)])
                batch.state = BatchState.SUCCESS
                current_app.logger.info('Succeed to import dataset batch %d/%s',
                                        batch.dataset_id, batch.event_time)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise InvalidArgumentException(details=e)
        else:
            db.session.rollback()


def _fail_move_file_routine(context, failed_file: str, failed_reason: str,
                            batch: DataBatch):
    with context.app_context():
        batch = db.session.query(DataBatch).with_for_update() \
            .filter_by(dataset_id=batch.dataset_id,
                       event_time=batch.event_time).first()
        current_app.logger.info('Failed to import dataset batch %d/%s',
                                batch.dataset_id, batch.event_time)
        # If dataset still exists
        if batch:
            batch.state = BatchState.FAILED
            batch.imported_file_num = 0
            batch.failed_source = '{}: {}'.format(failed_file, failed_reason)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise InvalidArgumentException(details=e)
        else:
            db.session.rollback()


def _aggregate_batches(dataset: Dataset) -> Dict:
    result = dataset.to_dict()
    result['state'] = BatchState.SUCCESS.value
    result['failed_source'] = []
    result['file_size'] = 0
    result['imported_file_num'] = 0
    result['file_num'] = 0
    for batch in dataset.data_batches:
        if batch.state == BatchState.FAILED:
            result['state'] = BatchState.FAILED.value
        if batch.state == BatchState.IMPORTING and \
            result['state'] != BatchState.FAILED.value:
            result['state'] = BatchState.IMPORTING.value
        if batch.failed_source:
            result['failed_source'].append(batch.failed_source)
        result['file_size'] += batch.file_size
        result['imported_file_num'] += batch.imported_file_num
        result['file_num'] += batch.file_num
    return result


def initialize_dataset_apis(api: Api):
    api.add_resource(DatasetApi, '/datasets')

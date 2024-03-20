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
import json
import logging
from typing import List

from sqlalchemy.orm import Session

from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.dataset.sparkapp.pipeline.util import \
    dataset_meta_path, dataset_features_path, dataset_hist_path
from fedlearner_webconsole.exceptions import NotFoundException
from fedlearner_webconsole.utils.file_manager import FileManager


class DatasetService(object):
    def __init__(self, session: Session):
        self._session = session
        self._file_manager = FileManager()

    def get_dataset_preview(self, dataset_id: int = 0) -> dict:
        dataset = self._session.query(Dataset).filter(
            Dataset.id == dataset_id).first()
        if not dataset:
            raise NotFoundException(f'Failed to find dataset: {dataset_id}')
        dataset_path = dataset.path
        # meta is generated from sparkapp/pipeline/analyzer.py
        meta_path = dataset_meta_path(dataset_path)
        # data format:
        # {
        #   'dtypes': {
        #     'f01': 'bigint'
        #   },
        #   'samples': [
        #     [1],
        #     [0],
        #   ],
        #   'metrics': {
        #     'f01': {
        #       'count': '2',
        #       'mean': '0.0015716767309123998',
        #       'stddev': '0.03961485047808605',
        #       'min': '0',
        #       'max': '1',
        #       'missing_count': '0'
        #     }
        #   }
        # }
        val = {}
        try:
            val = json.loads(self._file_manager.read(meta_path))
        except Exception as e:  # pylint: disable=broad-except
            logging.info(
                f'failed to read meta file, path: {meta_path}, err: {e}')
            return {}
        # feature is generated from sparkapp/pipeline/analyzer.py
        feature_path = dataset_features_path(dataset_path)
        try:
            val['metrics'] = json.loads(self._file_manager.read(feature_path))
        except Exception as e:  # pylint: disable=broad-except
            logging.info(
                f'failed to read feature file, path: {feature_path}, err: {e}')
        return val

    def feature_metrics(self, name: str, dataset_id: int = 0) -> dict:
        dataset = self._session.query(Dataset).filter(
            Dataset.id == dataset_id).first()
        if not dataset:
            raise NotFoundException(f'Failed to find dataset: {dataset_id}')
        dataset_path = dataset.path
        feature_path = dataset_features_path(dataset_path)
        # data format:
        # {
        #    'name': 'f01',
        #    'metrics': {
        #      'count': '2',
        #      'mean': '0.0015716767309123998',
        #      'stddev': '0.03961485047808605',
        #      'min': '0',
        #      'max': '1',
        #      'missing_count': '0'
        #    },
        #    'hist': {
        #      'x': [0.0, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5,
        #             0.6000000000000001, 0.7000000000000001, 0.8, 0.9, 1],
        #      'y': [12070, 0, 0, 0, 0, 0, 0, 0, 0, 19]
        #    }
        # }
        val = {}
        try:
            feature_data = json.loads(self._file_manager.read(feature_path))
            val['name'] = name
            val['metrics'] = feature_data.get(name, {})
        except Exception as e:  # pylint: disable=broad-except
            logging.info(
                f'failed to read feature file, path: {feature_path}, err: {e}')
        # hist is generated from sparkapp/pipeline/analyzer.py
        hist_path = dataset_hist_path(dataset_path)
        try:
            hist_data = json.loads(self._file_manager.read(hist_path))
            val['hist'] = hist_data.get(name, {})
        except Exception as e:  # pylint: disable=broad-except
            logging.info(
                f'failed to read hist file, path: {hist_path}, err: {e}')
        return val

    def get_datasets(self, project_id: int = 0) -> List[Dataset]:
        q = self._session.query(Dataset).order_by(Dataset.created_at.desc())
        if project_id > 0:
            q = q.filter(Dataset.project_id == project_id)
        return q.all()

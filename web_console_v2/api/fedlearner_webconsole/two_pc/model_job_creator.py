# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import logging
from typing import Tuple, Optional

from sqlalchemy.orm import Session
from fedlearner_webconsole.dataset.models import Dataset, ResourceState
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.mmgr.models import Model, ModelJob, ModelJobType, ModelJobGroup
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData
from fedlearner_webconsole.two_pc.resource_manager import ResourceManager


class ModelJobCreator(ResourceManager):
    """Create model job without configuration"""

    def __init__(self, session: Session, tid: str, data: TransactionData):
        super().__init__(tid, data)
        assert data.create_model_job_data is not None
        self._data = data.create_model_job_data
        self._session = session

    def _check_model_job(self) -> Tuple[bool, str]:
        model_job_name = self._data.model_job_name
        model_job = self._session.query(ModelJob).filter_by(name=model_job_name).first()
        if model_job:
            message = f'model job {model_job_name} already exist'
            logging.info('[model-job-2pc] prepare failed: %s', message)
            return False, message
        return True, ''

    def _check_model_job_group(self) -> Tuple[bool, str]:
        model_job_group_name = self._data.group_name
        # there is no model group for eval/predict model job
        if model_job_group_name:
            model_job_group = self._session.query(ModelJobGroup).filter_by(name=model_job_group_name).first()
            if model_job_group is None:
                message = f'model group {model_job_group_name} not exists'
                logging.info('[model-job-2pc] prepare failed: %s', message)
                return False, message
        return True, ''

    def _check_model(self) -> Tuple[bool, str]:
        model_uuid = self._data.model_uuid
        # there is no model for training model job
        if model_uuid:
            model = self._session.query(Model).filter_by(uuid=model_uuid).first()
            if model is None:
                message = f'model {self._data.model_uuid} not found'
                logging.info('[model-job-2pc] prepare failed: %s', message)
                return False, message
        return True, ''

    def _check_dataset(self) -> Tuple[bool, str]:
        if self._data.dataset_uuid:
            dataset: Dataset = self._session.query(Dataset).filter_by(uuid=self._data.dataset_uuid).first()
            if not dataset:
                message = f'dataset {self._data.dataset_uuid} not exists'
                logging.info('[model-job-2pc] prepare failed: %s', message)
                return False, message
            if dataset.get_frontend_state() != ResourceState.SUCCEEDED:
                message = f'dataset {self._data.dataset_uuid} is not succeeded'
                logging.info('[model-group-2pc] prepare failed: %s', message)
                return False, message
            if not dataset.is_published:
                message = f'dataset {self._data.dataset_uuid} is not published'
                logging.info('[model-job-2pc] prepare failed: %s', message)
                return False, message
        return True, ''

    def prepare(self) -> Tuple[bool, str]:
        check_fn_list = [self._check_model_job, self._check_model_job_group, self._check_model, self._check_dataset]
        for check_fn in check_fn_list:
            succeeded, message = check_fn()
            if not succeeded:
                return False, message
        logging.info('[model-job-2pc] prepare succeeded')
        return True, ''

    def _get_model_job_group_id(self) -> Optional[int]:
        if self._data.group_name:
            model_job_group = self._session.query(ModelJobGroup).filter_by(name=self._data.group_name).first()
            return model_job_group.id
        return None

    def _get_model_id(self) -> Optional[int]:
        if self._data.model_uuid:
            model = self._session.query(Model).filter_by(uuid=self._data.model_uuid).first()
            return model.id
        return None

    def _get_project_id(self) -> int:
        project = self._session.query(Project).filter_by(name=self._data.project_name).first()
        return project.id

    def _get_dataset_id(self) -> Optional[int]:
        if self._data.dataset_uuid:
            dataset = self._session.query(Dataset).filter_by(uuid=self._data.dataset_uuid).first()
            return dataset.id
        return None

    def commit(self) -> Tuple[bool, str]:
        model_job_group_id = self._get_model_job_group_id()
        model_id = self._get_model_id()
        project_id = self._get_project_id()
        dataset_id = self._get_dataset_id()
        coordinator = ParticipantService(
            self._session).get_participant_by_pure_domain_name(pure_domain_name=self._data.coordinator_pure_domain_name)
        coordinator_id = None
        if coordinator is not None:
            coordinator_id = coordinator.id
        model_job = ModelJob(name=self._data.model_job_name,
                             model_job_type=ModelJobType[self._data.model_job_type],
                             project_id=project_id,
                             uuid=self._data.model_job_uuid,
                             group_id=model_job_group_id,
                             dataset_id=dataset_id,
                             model_id=model_id,
                             workflow_uuid=self._data.workflow_uuid,
                             algorithm_type=self._data.algorithm_type,
                             coordinator_id=coordinator_id)
        self._session.add(model_job)
        logging.info('[model-job-2pc] commit succeeded')
        return True, ''

    def abort(self) -> Tuple[bool, str]:
        logging.info('[model-job-2pc] abort')
        # As we did not preserve any resource, do nothing
        return True, ''

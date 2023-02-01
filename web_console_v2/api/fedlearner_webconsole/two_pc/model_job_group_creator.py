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
from typing import Tuple

from sqlalchemy.orm import Session

from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.dataset.models import Dataset, ResourceState
from fedlearner_webconsole.mmgr.models import ModelJobGroup, ModelJobRole, GroupCreateStatus
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.two_pc.resource_manager import ResourceManager
from fedlearner_webconsole.setting.service import SettingService


class ModelJobGroupCreator(ResourceManager):

    def __init__(self, session: Session, tid: str, data: TransactionData):
        super().__init__(tid, data)
        assert data.create_model_job_group_data is not None
        self._data = data.create_model_job_group_data
        self._session = session

    def _check_project(self) -> Tuple[bool, str]:
        project_name = self._data.project_name
        project = self._session.query(Project).filter_by(name=project_name).first()
        if not project:
            message = f'project {self._data.model_job_group_name} not exists'
            logging.info('[model-group-2pc] prepare failed: %s', message)
            return False, message
        return True, ''

    def _check_group(self) -> Tuple[bool, str]:
        model_job_group_name = self._data.model_job_group_name
        model_job_group = self._session.query(ModelJobGroup).filter_by(name=model_job_group_name).first()
        if model_job_group:
            if model_job_group.uuid != self._data.model_job_group_uuid:
                message = f'model group {model_job_group_name} with different uuid already exist'
                logging.info('[model-group-2pc] prepare failed: %s', message)
                return False, message
        return True, ''

    def _check_dataset(self) -> Tuple[bool, str]:
        if self._data.dataset_uuid:
            dataset = self._session.query(Dataset).filter_by(uuid=self._data.dataset_uuid).first()
            if not dataset:
                message = f'dataset {self._data.dataset_uuid} not exists'
                logging.info('[model-group-2pc] prepare failed: %s', message)
                return False, message
            if dataset.get_frontend_state() != ResourceState.SUCCEEDED:
                message = f'dataset {self._data.dataset_uuid} is not succeeded'
                logging.info('[model-group-2pc] prepare failed: %s', message)
                return False, message
            if not dataset.is_published:
                message = f'dataset {self._data.dataset_uuid} is not published'
                logging.info('[model-group-2pc] prepare failed: %s', message)
                return False, message
        return True, ''

    def prepare(self) -> Tuple[bool, str]:
        check_fn_list = [self._check_project, self._check_group, self._check_dataset]
        for check_fn in check_fn_list:
            succeeded, message = check_fn()
            if not succeeded:
                return False, message
        logging.info('[model-group-2pc] prepare succeeded')
        return True, ''

    def commit(self) -> Tuple[bool, str]:
        model_job_group_name = self._data.model_job_group_name
        project = self._session.query(Project).filter_by(name=self._data.project_name).first()
        group = self._session.query(ModelJobGroup).filter_by(name=model_job_group_name).first()
        dataset_id = None
        if self._data.dataset_uuid:
            dataset_id = self._session.query(Dataset).filter_by(uuid=self._data.dataset_uuid).first().id
        coordinator = ParticipantService(
            self._session).get_participant_by_pure_domain_name(pure_domain_name=self._data.coordinator_pure_domain_name)
        coordinator_id = None
        if coordinator is not None:
            coordinator_id = coordinator.id
        if not group:
            group = ModelJobGroup(name=model_job_group_name,
                                  uuid=self._data.model_job_group_uuid,
                                  project_id=project.id,
                                  dataset_id=dataset_id,
                                  authorized=False,
                                  role=ModelJobRole.PARTICIPANT,
                                  algorithm_type=AlgorithmType[self._data.algorithm_type],
                                  coordinator_id=coordinator_id)
            participants = ParticipantService(self._session).get_participants_by_project(project.id)
            participants_info = ParticipantsInfo(participants_map={
                p.pure_domain_name(): ParticipantInfo(auth_status=AuthStatus.PENDING.name) for p in participants
            })
            participants_info.participants_map[
                self._data.coordinator_pure_domain_name].auth_status = AuthStatus.AUTHORIZED.name
            pure_domain_name = SettingService.get_system_info().pure_domain_name
            participants_info.participants_map[pure_domain_name].auth_status = AuthStatus.PENDING.name
            group.set_participants_info(participants_info)
            self._session.add(group)
            group.status = GroupCreateStatus.SUCCEEDED
        logging.info('[model-group-2pc] commit succeeded')
        return True, ''

    def abort(self) -> Tuple[bool, str]:
        logging.info('[model-group-2pc] abort')
        group = self._session.query(ModelJobGroup).filter_by(name=self._data.model_job_group_name).first()
        if group is not None:
            group.status = GroupCreateStatus.FAILED
        # As we did not preserve any resource, do nothing
        return True, ''

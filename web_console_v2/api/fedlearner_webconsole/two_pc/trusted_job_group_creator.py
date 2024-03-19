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
from fedlearner_webconsole.review.ticket_helper import get_ticket_helper
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.tee.models import TrustedJobGroup, GroupCreateStatus
from fedlearner_webconsole.proto.tee_pb2 import ParticipantDatasetList, ParticipantDataset
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData
from fedlearner_webconsole.two_pc.resource_manager import ResourceManager
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.algorithm.fetcher import AlgorithmFetcher
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.exceptions import NotFoundException


class TrustedJobGroupCreator(ResourceManager):

    def __init__(self, session: Session, tid: str, data: TransactionData):
        super().__init__(tid, data)
        assert data.create_trusted_job_group_data is not None
        self._data = data.create_trusted_job_group_data
        self._session = session
        self._project_id = None
        self.pure_domain_name = SettingService.get_system_info().pure_domain_name

    def _check_ticket(self) -> Tuple[bool, str]:
        validate = get_ticket_helper(self._session).validate_ticket(
            self._data.ticket_uuid, lambda ticket: ticket.details.uuid == self._data.uuid)
        if not validate:
            message = f'ticket {self._data.ticket_uuid} is not valid'
            logging.info('[trusted-group-2pc] prepare failed: %s', message)
            return False, message
        return True, ''

    def _check_group(self) -> Tuple[bool, str]:
        name = self._data.name
        project_name = self._data.project_name
        project = self._session.query(Project).filter_by(name=project_name).first()
        self._project_id = project.id
        group = self._session.query(TrustedJobGroup).filter_by(name=name, project_id=project.id).first()
        if group is not None and group.uuid != self._data.uuid:
            message = f'trusted job group {name} in project {project_name} with different uuid already exists'
            logging.info('[trusted-group-2pc] prepare failed: %s', message)
            return False, message
        return True, ''

    def _check_algorithm(self) -> Tuple[bool, str]:
        try:
            algorithm = AlgorithmFetcher(self._project_id).get_algorithm(self._data.algorithm_uuid)
            if algorithm.type != AlgorithmType.TRUSTED_COMPUTING.name:
                message = f'algorithm {self._data.algorithm_uuid} is not TRUSTED_COMPUTING type'
                logging.info('[trusted-group-2pc] prepare failed: %s', message)
                return False, message
        except NotFoundException as e:
            message = e.message
            logging.info('[trusted-group-2pc] prepare failed: %s', message)
            return False, message
        return True, ''

    def _check_participant_dataset(self) -> Tuple[bool, str]:
        for dnd in self._data.domain_name_datasets:
            if dnd.pure_domain_name == self.pure_domain_name:
                dataset = self._session.query(Dataset).filter_by(uuid=dnd.dataset_uuid, name=dnd.dataset_name).first()
                if dataset is None:
                    message = f'dataset {dnd.dataset_uuid} not exists'
                    logging.info('[trusted-group-2pc] prepare failed: %s', message)
                    return False, message
                if not dataset.is_published:
                    message = f'dataset {dnd.dataset_uuid} is not published'
                    logging.info('[trusted-group-2pc] prepare failed: %s', message)
                    return False, message
            else:
                participant = ParticipantService(
                    self._session).get_participant_by_pure_domain_name(pure_domain_name=dnd.pure_domain_name)
                if participant is None:
                    message = f'participant with pure domain name {dnd.pure_domain_name} not exists'
                    logging.info('[trusted-group-2pc] prepare failed: %s', message)
                    return False, message
        return True, ''

    def _check_participant(self) -> Tuple[bool, str]:
        for pure_domain_name in [self._data.coordinator_pure_domain_name, self._data.analyzer_pure_domain_name]:
            if pure_domain_name != self.pure_domain_name:
                participant = ParticipantService(
                    self._session).get_participant_by_pure_domain_name(pure_domain_name=pure_domain_name)
                if participant is None:
                    message = f'participant with pure domain name {pure_domain_name} not exists'
                    logging.info('[trusted-group-2pc] prepare failed: %s', message)
                    return False, message
        return True, ''

    def prepare(self) -> Tuple[bool, str]:
        # _check_algorithm should be after _check_group
        check_fn_list = [
            self._check_ticket,
            self._check_group,
            self._check_algorithm,
            self._check_participant_dataset,
            self._check_participant,
        ]
        for check_fn in check_fn_list:
            succeeded, message = check_fn()
            if not succeeded:
                return False, message
        logging.info('[trusted-group-2pc] prepare succeeded')
        return True, ''

    def commit(self) -> Tuple[bool, str]:
        coordinator_pure_domain_name = self._data.coordinator_pure_domain_name
        # The coordinator has already created in POST api so do nothing
        if self.pure_domain_name == coordinator_pure_domain_name:
            logging.info('[trusted-group-2pc] commit succeeded')
            return True, ''
        name = self._data.name
        uuid = self._data.uuid
        project = self._session.query(Project).filter_by(name=self._data.project_name).first()
        coordinator_id = ParticipantService(
            self._session).get_participant_by_pure_domain_name(pure_domain_name=coordinator_pure_domain_name).id
        if self.pure_domain_name == self._data.analyzer_pure_domain_name:
            analyzer_id = 0
        else:
            analyzer_id = ParticipantService(self._session).get_participant_by_pure_domain_name(
                pure_domain_name=self._data.analyzer_pure_domain_name).id
        dataset_id = None
        participant_datasets = ParticipantDatasetList()
        for dnd in self._data.domain_name_datasets:
            if dnd.pure_domain_name == self.pure_domain_name:
                dataset = self._session.query(Dataset).filter_by(uuid=dnd.dataset_uuid).first()
                dataset_id = dataset.id
            else:
                participant = ParticipantService(
                    self._session).get_participant_by_pure_domain_name(pure_domain_name=dnd.pure_domain_name)
                participant_datasets.items.append(
                    ParticipantDataset(participant_id=participant.id, uuid=dnd.dataset_uuid, name=dnd.dataset_name))
        participants = ParticipantService(self._session).get_participants_by_project(project.id)
        unauth_participant_ids = [p.id for p in participants if p.id != coordinator_id]
        group = self._session.query(TrustedJobGroup).filter_by(uuid=uuid).first()
        if not group:
            group = TrustedJobGroup(
                name=name,
                uuid=uuid,
                latest_version=0,
                creator_username=self._data.creator_username,
                project_id=project.id,
                coordinator_id=coordinator_id,
                analyzer_id=analyzer_id,
                ticket_uuid=self._data.ticket_uuid,
                ticket_status=TicketStatus.APPROVED,
                status=GroupCreateStatus.SUCCEEDED,
                algorithm_uuid=self._data.algorithm_uuid,
                dataset_id=dataset_id,
            )
            group.set_participant_datasets(participant_datasets)
            group.set_unauth_participant_ids(unauth_participant_ids)
            self._session.add(group)
        logging.info('[trusted-group-2pc] commit succeeded')
        return True, ''

    def abort(self) -> Tuple[bool, str]:
        logging.info('[trusted-group-2pc] abort')
        # As we did not preserve any resource, do nothing
        return True, ''

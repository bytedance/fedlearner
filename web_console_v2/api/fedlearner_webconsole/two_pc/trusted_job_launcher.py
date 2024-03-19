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
from fedlearner_webconsole.tee.services import TrustedJobGroupService
from fedlearner_webconsole.tee.models import TrustedJobGroup
from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData
from fedlearner_webconsole.two_pc.resource_manager import ResourceManager
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.algorithm.fetcher import AlgorithmFetcher
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.exceptions import NotFoundException
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.participant.services import ParticipantService


class TrustedJobLauncher(ResourceManager):
    """Launch a configured trusted job based on the config of trusted job group"""

    def __init__(self, session: Session, tid: str, data: TransactionData):
        super().__init__(tid, data)
        assert data.launch_trusted_job_data is not None
        self._data = data.launch_trusted_job_data
        self._session = session
        self._group = None

    def _check_group(self) -> Tuple[bool, str]:
        if self._data.group_uuid:
            group: TrustedJobGroup = self._session.query(TrustedJobGroup).filter_by(uuid=self._data.group_uuid).first()
            if group is not None:
                self._group = group
                return True, ''
        message = f'trusted job group {self._data.group_uuid} not found'
        logging.info('[launch-trusted-job-2pc] prepare failed: %s', message)
        return False, message

    def _check_version(self) -> Tuple[bool, str]:
        self_pure_domain_name = SettingService.get_system_info().pure_domain_name
        if (self._group.latest_version >= self._data.version and
                self._data.initiator_pure_domain_name != self_pure_domain_name):
            message = (f'the latest version of trusted job group {self._data.group_uuid} '
                       f'is greater than or equal to the given version')
            logging.info('[launch-trusted-job-2pc] prepare failed: %s', message)
            return False, message
        return True, ''

    def _check_auth(self) -> Tuple[bool, str]:
        if self._group.auth_status != AuthStatus.AUTHORIZED:
            message = f'trusted job group {self._data.group_uuid} not authorized'
            logging.info('[launch-trusted-job-2pc] prepare failed: %s', message)
            return False, message
        return True, ''

    def _check_algorithm(self) -> Tuple[bool, str]:
        try:
            algorithm = AlgorithmFetcher(self._group.project_id).get_algorithm(self._group.algorithm_uuid)
            if algorithm.type != AlgorithmType.TRUSTED_COMPUTING.name:
                message = f'algorithm {self._group.algorithm_uuid} is not TRUSTED_COMPUTING type'
                logging.info('[launch-trusted-job-2pc] prepare failed: %s', message)
                return False, message
        except NotFoundException as e:
            message = e.message
            logging.info('[launch-trusted-job-2pc] prepare failed: %s', message)
            return False, message
        return True, ''

    def _check_dataset(self) -> Tuple[bool, str]:
        if self._group.dataset_id is not None:
            dataset: Dataset = self._session.query(Dataset).get(self._group.dataset_id)
            if dataset is None or not dataset.is_published:
                message = f'dataset {self._group.dataset_id} is not found'
                logging.info('[launch-trusted-job-2pc] prepare failed: %s', message)
                return False, message
        return True, ''

    def _check_initiator(self) -> Tuple[bool, str]:
        init_pure_dn = self._data.initiator_pure_domain_name
        if SettingService.get_system_info().pure_domain_name == init_pure_dn:
            return True, ''
        participant = ParticipantService(self._session).get_participant_by_pure_domain_name(init_pure_dn)
        if participant is None:
            message = f'initiator {self._data.initiator_pure_domain_name} is not found'
            logging.info('[launch-trusted-job-2pc] prepare failed: %s', message)
            return False, message
        return True, ''

    def prepare(self) -> Tuple[bool, str]:
        # _check_group should be the first
        check_fn_list = [
            self._check_group,
            self._check_version,
            self._check_auth,
            self._check_algorithm,
            self._check_dataset,
            self._check_initiator,
        ]
        for check_fn in check_fn_list:
            succeeded, message = check_fn()
            if not succeeded:
                return False, message
        logging.info('[launch-trusted-job-2pc] prepare succeeded')
        return True, ''

    def commit(self) -> Tuple[bool, str]:
        group: TrustedJobGroup = self._session.query(TrustedJobGroup).filter_by(uuid=self._data.group_uuid).first()
        pure_dn = self._data.initiator_pure_domain_name
        if SettingService.get_system_info().pure_domain_name == pure_dn:
            coordinator_id = 0
        else:
            participant = ParticipantService(self._session).get_participant_by_pure_domain_name(pure_dn)
            coordinator_id = participant.id
        TrustedJobGroupService(self._session).launch_trusted_job(group, self._data.uuid, self._data.version,
                                                                 coordinator_id)
        logging.info(f'[launch-trusted-job-2pc] commit succeeded for group {group.name}')
        return True, ''

    def abort(self) -> Tuple[bool, str]:
        logging.info('[launch-trusted-job-2pc] abort')
        # As we did not preserve any resource, do nothing
        return True, ''

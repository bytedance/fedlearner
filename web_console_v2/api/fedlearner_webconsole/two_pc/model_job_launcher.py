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
from fedlearner_webconsole.mmgr.service import ModelJobGroupService
from fedlearner_webconsole.mmgr.models import ModelJobGroup, ModelJobRole
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData
from fedlearner_webconsole.two_pc.resource_manager import ResourceManager


class ModelJobLauncher(ResourceManager):
    """Launch a configured model job based on the config of model job group"""

    def __init__(self, session: Session, tid: str, data: TransactionData):
        super().__init__(tid, data)
        assert data.create_model_job_data is not None
        self._data = data.create_model_job_data
        self._session = session

    def prepare(self) -> Tuple[bool, str]:
        if self._data.group_uuid is None:
            message = 'group_uuid not found in create_model_job_data'
            logging.info('[launch-model-job-2pc] prepare failed: %s', message)
            return False, message
        group: ModelJobGroup = self._session.query(ModelJobGroup).filter_by(uuid=self._data.group_uuid).first()
        if group is None:
            message = f'model group not found by uuid {self._data.group_uuid}'
            logging.info('[launch-model-job-2pc] prepare failed: %s', message)
            return False, message
        if group.role == ModelJobRole.PARTICIPANT and not group.authorized:
            message = f'model group {self._data.group_uuid} not authorized to coordinator'
            logging.info('[launch-model-job-2pc] prepare failed: %s', message)
            return False, message
        if group.config is None:
            message = f'the config of model group {group.name} not found'
            logging.info('[launch-model-job-2pc] prepare failed: %s', message)
            return False, message
        # the latest version of group at coordinator is the same with the given version
        if group.latest_version >= self._data.version and group.role == ModelJobRole.PARTICIPANT:
            message = f'the latest version of model group {group.name} is larger than or equal to the given version'
            logging.info('[launch-model-job-2pc] prepare failed: %s', message)
            return False, message
        if group.algorithm_id is not None and group.algorithm is None:
            message = f'the algorithm {group.algorithm_id} of group {group.name} is not found'
            logging.warning('[launch-model-job-2pc] prepare failed: %s', message)
            return False, message
        return True, ''

    def commit(self) -> Tuple[bool, str]:
        group: ModelJobGroup = self._session.query(ModelJobGroup).filter_by(uuid=self._data.group_uuid).first()

        ModelJobGroupService(self._session).launch_model_job(group=group,
                                                             name=self._data.model_job_name,
                                                             uuid=self._data.model_job_uuid,
                                                             version=self._data.version)
        logging.info(f'[launch-model-job-2pc] commit succeeded for group {group.name}')
        return True, ''

    def abort(self) -> Tuple[bool, str]:
        logging.info('[model-job-2pc] abort')
        # As we did not preserve any resource, do nothing
        return True, ''

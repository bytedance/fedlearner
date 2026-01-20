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

from fedlearner_webconsole.dataset.models import DatasetJobStage, DatasetJobState
from fedlearner_webconsole.dataset.local_controllers import DatasetJobStageLocalController
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData
from fedlearner_webconsole.two_pc.resource_manager import ResourceManager


class DatasetJobStageStopper(ResourceManager):

    def __init__(self, session: Session, tid: str, data: TransactionData):
        super().__init__(tid, data)
        assert data.stop_dataset_job_stage_data is not None
        self._data = data.stop_dataset_job_stage_data
        self._session = session

    def prepare(self) -> Tuple[bool, str]:
        dataset_job_stage: DatasetJobStage = self._session.query(DatasetJobStage).filter_by(
            uuid=self._data.dataset_job_stage_uuid).first()
        if dataset_job_stage is None:
            message = 'dataset_job_stage not found'
            logging.warning(
                f'[dataset_job_stage stop 2pc] prepare: {message}, uuid: {self._data.dataset_job_stage_uuid}')
            return False, message
        if dataset_job_stage.state in [DatasetJobState.SUCCEEDED, DatasetJobState.FAILED]:
            message = 'dataset_job_stage state check failed! ' \
                f'current state {dataset_job_stage.state.value} cannot stop'
            logging.warning(
                f'[dataset_job_stage stop 2pc] prepare: {message}, uuid: {self._data.dataset_job_stage_uuid}')
            return False, message
        return True, ''

    def commit(self) -> Tuple[bool, str]:
        # use x lock here, it will keep waiting if it find other lock until lock release or timeout.
        # we dont't use s lock as it may raise deadlock exception.
        dataset_job_stage: DatasetJobStage = self._session.query(DatasetJobStage).populate_existing().with_for_update(
        ).filter_by(uuid=self._data.dataset_job_stage_uuid).first()
        # allow stop to stop state transfer
        if dataset_job_stage.state == DatasetJobState.STOPPED:
            return True, ''
        try:
            DatasetJobStageLocalController(session=self._session).stop(dataset_job_stage)
        except RuntimeError as e:
            logging.error(f'[dataset_job_stage stop 2pc] commit: {e}, uuid: {self._data.dataset_job_stage_uuid}')
            raise
        return True, ''

    def abort(self) -> Tuple[bool, str]:
        logging.info('[dataset_job_stage stop 2pc] abort')
        return True, ''

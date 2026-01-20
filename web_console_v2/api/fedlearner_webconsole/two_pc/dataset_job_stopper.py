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

from fedlearner_webconsole.workflow.workflow_controller import stop_workflow_locally
from fedlearner_webconsole.dataset.models import DatasetJob, DatasetJobState
from fedlearner_webconsole.dataset.services import DatasetJobService
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData
from fedlearner_webconsole.two_pc.resource_manager import ResourceManager


class DatasetJobStopper(ResourceManager):

    def __init__(self, session: Session, tid: str, data: TransactionData):
        super().__init__(tid, data)
        assert data.stop_dataset_job_data is not None
        self._data = data.stop_dataset_job_data
        self._session = session

    def prepare(self) -> Tuple[bool, str]:
        dataset_job = self._session.query(DatasetJob).populate_existing().with_for_update(read=True).filter_by(
            uuid=self._data.dataset_job_uuid).first()
        if dataset_job is None:
            message = 'dataset_job not found'
            logging.warning(f'[dataset_job stop 2pc] prepare: {message}, uuid: {self._data.dataset_job_uuid}')
            return False, message
        if dataset_job.state in [DatasetJobState.SUCCEEDED, DatasetJobState.FAILED]:
            message = f'dataset_job state check failed! current state {dataset_job.state.value} cannot stop, ' \
                f'expected: {DatasetJobState.PENDING.value}, {DatasetJobState.RUNNING.value} or ' \
                f'{DatasetJobState.STOPPED.value}, uuid is {self._data.dataset_job_uuid}'
            logging.warning(f'[dataset_job stop 2pc] prepare: {message}, uuid: {self._data.dataset_job_uuid}')
            return False, message
        return True, ''

    def commit(self) -> Tuple[bool, str]:
        dataset_job = self._session.query(DatasetJob).populate_existing().with_for_update().filter_by(
            uuid=self._data.dataset_job_uuid).first()
        # allow stop to stop state transfer
        if dataset_job.state == DatasetJobState.STOPPED:
            return True, ''
        try:
            if dataset_job.workflow is not None:
                stop_workflow_locally(self._session, dataset_job.workflow)
            else:
                logging.info(f'[dataset_job stop 2pc] commit: workflow not found, just skip, ' \
                    f'uuid: {self._data.dataset_job_uuid}')
        except RuntimeError as e:
            logging.error(f'[dataset_job stop 2pc] commit: {e}, uuid: {self._data.dataset_job_uuid}')
            raise
        DatasetJobService(self._session).finish_dataset_job(dataset_job=dataset_job,
                                                            finish_state=DatasetJobState.STOPPED)
        return True, ''

    def abort(self) -> Tuple[bool, str]:
        logging.info('[dataset_job stop 2pc] abort')
        return True, ''

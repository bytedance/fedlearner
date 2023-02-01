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

from fedlearner_webconsole.workflow.workflow_controller import start_workflow_locally
from fedlearner_webconsole.dataset.models import DatasetJob, DatasetJobState
from fedlearner_webconsole.dataset.services import DatasetJobService
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData
from fedlearner_webconsole.two_pc.resource_manager import ResourceManager


class DatasetJobLauncher(ResourceManager):

    def __init__(self, session: Session, tid: str, data: TransactionData):
        super().__init__(tid, data)
        assert data.launch_dataset_job_data is not None
        self._data = data.launch_dataset_job_data
        self._session = session

    def prepare(self) -> Tuple[bool, str]:
        dataset_job = self._session.query(DatasetJob).populate_existing().with_for_update(read=True).filter_by(
            uuid=self._data.dataset_job_uuid).first()
        if dataset_job is None:
            message = f'failed to find dataset_job, uuid is {self._data.dataset_job_uuid}'
            logging.warning(f'[dataset_job launch 2pc] prepare: {message}, uuid: {self._data.dataset_job_uuid}')
            return False, message
        if not dataset_job.state in [DatasetJobState.PENDING, DatasetJobState.RUNNING]:
            message = f'dataset_job state check failed! current: {dataset_job.state.value}, ' \
                f'expected: {DatasetJobState.PENDING.value} or {DatasetJobState.RUNNING.value},' \
                f'uuid is {self._data.dataset_job_uuid}'
            logging.warning(f'[dataset_job launch 2pc] prepare: {message}, uuid: {self._data.dataset_job_uuid}')
            return False, message
        if dataset_job.workflow is None:
            message = f'failed to find workflow, uuid is {self._data.dataset_job_uuid}'
            logging.warning(f'[dataset_job launch 2pc] prepare: {message}, uuid: {self._data.dataset_job_uuid}')
            return False, message
        return True, ''

    def commit(self) -> Tuple[bool, str]:
        dataset_job = self._session.query(DatasetJob).populate_existing().with_for_update().filter_by(
            uuid=self._data.dataset_job_uuid).first()
        if dataset_job.state == DatasetJobState.RUNNING:
            return True, ''
        if dataset_job.state != DatasetJobState.PENDING:
            message = f'dataset_job state check failed! current: {dataset_job.state.value}, ' \
                f'expected: {DatasetJobState.PENDING.value} or {DatasetJobState.RUNNING.value},' \
                f'uuid is {self._data.dataset_job_uuid}'
            logging.warning(f'[dataset_job launch 2pc] prepare: {message}, uuid: {self._data.dataset_job_uuid}')
            return False, message
        try:
            start_workflow_locally(self._session, dataset_job.workflow)
        except RuntimeError as e:
            logging.error(f'[dataset_job launch 2pc] commit: {e}, uuid: {self._data.dataset_job_uuid}')
            raise
        DatasetJobService(self._session).start_dataset_job(dataset_job)
        return True, ''

    def abort(self) -> Tuple[bool, str]:
        logging.info('[dataset_job launch 2pc] abort')
        return True, ''

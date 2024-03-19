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

from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData
from fedlearner_webconsole.two_pc.resource_manager import ResourceManager
from fedlearner_webconsole.tee.models import TrustedJob, TrustedJobStatus
from fedlearner_webconsole.tee.services import TrustedJobService


class TrustedJobStopper(ResourceManager):

    def __init__(self, session: Session, tid: str, data: TransactionData):
        super().__init__(tid, data)
        assert data.stop_trusted_job_data is not None
        self._data = data.stop_trusted_job_data
        self._session = session

    def prepare(self) -> Tuple[bool, str]:
        trusted_job = self._session.query(TrustedJob).filter_by(uuid=self._data.uuid).first()
        if trusted_job is None:
            message = f'failed to find trusted job by uuid {self._data.uuid}'
            logging.info(f'[stop-trusted-job-2pc] prepare: {message}')
            return False, message
        if trusted_job.get_status() == TrustedJobStatus.PENDING:
            message = 'trusted job status PENDING is unstoppable'
            logging.info(f'[stop-trusted-job-2pc] prepare: {message}')
            return False, message
        return True, ''

    def commit(self) -> Tuple[bool, str]:
        trusted_job = self._session.query(TrustedJob).filter_by(uuid=self._data.uuid).first()
        if trusted_job is None:
            logging.error(f'[trusted-job-stop-2pc] commit: trusted job with uuid {self._data.uuid} not found')
            return True, ''
        TrustedJobService(self._session).stop_trusted_job(trusted_job)
        if trusted_job.get_status() != TrustedJobStatus.STOPPED:
            logging.warning(f'[trusted-job-stop-2pc] commit: stop trusted job with uuid {self._data.uuid} '
                            f'ending with status {trusted_job.get_status()}')
        return True, ''

    def abort(self) -> Tuple[bool, str]:
        logging.info('[trusted-job-stop-2pc] abort')
        return True, ''

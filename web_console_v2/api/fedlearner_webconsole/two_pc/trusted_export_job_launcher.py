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
from fedlearner_webconsole.tee.services import TrustedJobService
from fedlearner_webconsole.tee.models import TrustedJob, TrustedJobStatus
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData
from fedlearner_webconsole.two_pc.resource_manager import ResourceManager
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus


class TrustedExportJobLauncher(ResourceManager):
    """Launch a configured trusted export job"""

    def __init__(self, session: Session, tid: str, data: TransactionData):
        super().__init__(tid, data)
        assert data.launch_trusted_export_job_data is not None
        self._data = data.launch_trusted_export_job_data
        self._session = session
        self._tee_export_job = None

    def _check_trusted_export_job(self) -> Tuple[bool, str]:
        self._tee_export_job = self._session.query(TrustedJob).filter_by(uuid=self._data.uuid).first()
        if self._tee_export_job is None:
            message = f'trusted export job {self._data.uuid} not found'
            logging.info('[launch-trusted-export-job-2pc] prepare failed: %s', message)
            return False, message
        return True, ''

    def _check_auth(self) -> Tuple[bool, str]:
        if self._tee_export_job.auth_status != AuthStatus.AUTHORIZED:
            message = f'trusted export job {self._data.uuid} not authorized'
            logging.info('[launch-trusted-export-job-2pc] prepare failed: %s', message)
            return False, message
        return True, ''

    def prepare(self) -> Tuple[bool, str]:
        # _check_trusted_export_job should be the first
        check_fn_list = [
            self._check_trusted_export_job,
            self._check_auth,
        ]
        for check_fn in check_fn_list:
            succeeded, message = check_fn()
            if not succeeded:
                return False, message
        logging.info('[launch-trusted-export-job-2pc] prepare succeeded')
        return True, ''

    def commit(self) -> Tuple[bool, str]:
        tee_export_job = self._session.query(TrustedJob).filter_by(uuid=self._data.uuid).first()
        if tee_export_job.coordinator_id == 0 or tee_export_job.group.analyzer_id == 0:
            TrustedJobService(self._session).launch_trusted_export_job(tee_export_job)
        else:
            tee_export_job.status = TrustedJobStatus.SUCCEEDED
        return True, ''

    def abort(self) -> Tuple[bool, str]:
        logging.info('[launch-trusted-export-job-2pc] abort')
        # As we did not preserve any resource, do nothing
        return True, ''

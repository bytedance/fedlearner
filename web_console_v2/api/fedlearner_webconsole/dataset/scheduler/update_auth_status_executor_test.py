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

import unittest
from unittest.mock import patch, MagicMock

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorResult
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobKind, DatasetJobSchedulerState, \
    DatasetJobState, DatasetKindV2, DatasetType
from fedlearner_webconsole.dataset.scheduler.update_auth_status_executor import UpdateAuthStatusExecutor
from fedlearner_webconsole.proto.project_pb2 import ParticipantInfo, ParticipantsInfo
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus


class UpdateAuthStatusExecutorTest(NoWebServerTestCase):
    _PROJECT_ID = 1
    _WORKFLOW_ID = 1
    _INPUT_DATASET_ID = 1
    _OUTPUT_DATASET_ID = 2
    _OUTPUT_DATASET_2_ID = 3

    def setUp(self) -> None:
        super().setUp()
        with db.session_scope() as session:
            dataset_job_1 = DatasetJob(id=1,
                                       uuid='dataset_job_1 uuid',
                                       project_id=self._PROJECT_ID,
                                       input_dataset_id=self._INPUT_DATASET_ID,
                                       output_dataset_id=self._OUTPUT_DATASET_ID,
                                       kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                       state=DatasetJobState.SUCCEEDED,
                                       coordinator_id=0,
                                       workflow_id=0,
                                       scheduler_state=DatasetJobSchedulerState.STOPPED)
            session.add(dataset_job_1)
            output_dataset_1 = Dataset(id=self._OUTPUT_DATASET_ID,
                                       uuid='dataset_1 uuid',
                                       name='default dataset_1',
                                       dataset_type=DatasetType.PSI,
                                       comment='test comment',
                                       path='/data/dataset/123',
                                       project_id=self._PROJECT_ID,
                                       dataset_kind=DatasetKindV2.PROCESSED,
                                       is_published=True)
            participants_info = ParticipantsInfo(
                participants_map={
                    'coordinator-domain-name': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'participant-domain-name': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                })
            output_dataset_1.set_participants_info(participants_info=participants_info)
            session.add(output_dataset_1)
            dataset_job_2 = DatasetJob(id=2,
                                       uuid='dataset_job_2 uuid',
                                       project_id=self._PROJECT_ID,
                                       input_dataset_id=self._INPUT_DATASET_ID,
                                       output_dataset_id=self._OUTPUT_DATASET_2_ID,
                                       kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                       state=DatasetJobState.PENDING,
                                       coordinator_id=0,
                                       workflow_id=0,
                                       scheduler_state=DatasetJobSchedulerState.STOPPED)
            session.add(dataset_job_2)
            output_dataset_2 = Dataset(id=self._OUTPUT_DATASET_2_ID,
                                       uuid='dataset_2 uuid',
                                       name='default dataset_1',
                                       dataset_type=DatasetType.PSI,
                                       comment='test comment',
                                       path='/data/dataset/123',
                                       project_id=self._PROJECT_ID,
                                       dataset_kind=DatasetKindV2.PROCESSED,
                                       is_published=True)
            participants_info = ParticipantsInfo(
                participants_map={
                    'coordinator-domain-name': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'participant-domain-name': ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                })
            output_dataset_2.set_participants_info(participants_info=participants_info)
            session.add(output_dataset_2)
            session.commit()

    def test_get_item_ids(self):
        update_auth_status_executor = UpdateAuthStatusExecutor()
        self.assertEqual(update_auth_status_executor.get_item_ids(), [3])

    @patch('fedlearner_webconsole.dataset.controllers.DatasetJobController.update_auth_status_cache')
    def test_run_item(self, mock_update_auth_status_cache: MagicMock):

        update_auth_status_executor = UpdateAuthStatusExecutor()
        with db.session_scope() as session:
            executor_result = update_auth_status_executor.run_item(3)
            self.assertEqual(executor_result, ExecutorResult.SUCCEEDED)
            mock_update_auth_status_cache.assert_called_once()


if __name__ == '__main__':
    unittest.main()

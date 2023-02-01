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
from unittest.mock import MagicMock, PropertyMock, patch

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.auth_service import AuthService
from fedlearner_webconsole.dataset.models import (Dataset, DatasetKindV2, ImportType, DatasetType, DatasetJob,
                                                  DatasetJobKind, DatasetJobState)
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.flag.models import _Flag
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from testing.no_web_server_test_case import NoWebServerTestCase


class AuthServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            dataset = Dataset(id=1,
                              uuid='dataset uuid',
                              name='default dataset',
                              dataset_type=DatasetType.PSI,
                              comment='test comment',
                              path='/data/dataset/123',
                              project_id=1,
                              dataset_kind=DatasetKindV2.PROCESSED,
                              is_published=True,
                              import_type=ImportType.COPY,
                              auth_status=AuthStatus.AUTHORIZED)
            session.add(dataset)
            dataset_job = DatasetJob(uuid='dataset_job uuid',
                                     kind=DatasetJobKind.DATA_ALIGNMENT,
                                     state=DatasetJobState.PENDING,
                                     project_id=1,
                                     workflow_id=0,
                                     input_dataset_id=0,
                                     output_dataset_id=1,
                                     coordinator_id=0)
            session.add(dataset_job)
            session.commit()

    @patch('fedlearner_webconsole.project.services.SettingService.get_system_info')
    def test_initialize_participants_info_as_coordinator(self, mock_system_info: MagicMock):
        mock_system_info.return_value = SystemInfo(pure_domain_name='test-domain-name-coordinator', name='coordinator')
        particiapnt_1 = Participant(id=1, name='test_participant_1', domain_name='fl-test-domain-name-1.com')
        particiapnt_2 = Participant(id=2, name='test_participant_2', domain_name='fl-test-domain-name-2.com')
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            AuthService(session=session, dataset_job=dataset_job).initialize_participants_info_as_coordinator(
                participants=[particiapnt_1, particiapnt_2])
            self.assertEqual(
                dataset_job.output_dataset.get_participants_info().participants_map['test-domain-name-1'].auth_status,
                AuthStatus.PENDING.value)
            self.assertEqual(
                dataset_job.output_dataset.get_participants_info().participants_map['test-domain-name-2'].auth_status,
                AuthStatus.PENDING.value)
            self.assertEqual(
                dataset_job.output_dataset.get_participants_info().participants_map['test-domain-name-coordinator'].
                auth_status, AuthStatus.AUTHORIZED.value)

    def test_initialize_participants_info_as_participant(self):
        participants_info = ParticipantsInfo(
            participants_map={
                'test-domain-name-coordinator': ParticipantInfo(auth_status='AUTHORIZED'),
                'test-domain-name-1': ParticipantInfo(auth_status='PENDING')
            })
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            AuthService(session=session, dataset_job=dataset_job).initialize_participants_info_as_participant(
                participants_info=participants_info)
            self.assertEqual(
                dataset_job.output_dataset.get_participants_info().participants_map['test-domain-name-1'].auth_status,
                AuthStatus.PENDING.value)
            self.assertEqual(
                dataset_job.output_dataset.get_participants_info().participants_map['test-domain-name-coordinator'].
                auth_status, AuthStatus.AUTHORIZED.value)

    def test_update_auth_status(self):
        participants_info = ParticipantsInfo(
            participants_map={
                'test-domain-name-coordinator': ParticipantInfo(auth_status='AUTHORIZED'),
                'test-domain-name-1': ParticipantInfo(auth_status='PENDING')
            })
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            dataset_job.output_dataset.set_participants_info(participants_info)
            AuthService(session=session, dataset_job=dataset_job).update_auth_status(domain_name='test-domain-name-1',
                                                                                     auth_status=AuthStatus.AUTHORIZED)
            self.assertEqual(
                dataset_job.output_dataset.get_participants_info().participants_map['test-domain-name-1'].auth_status,
                AuthStatus.AUTHORIZED.value)

    @patch('fedlearner_webconsole.flag.models.Flag.DATASET_AUTH_STATUS_CHECK_ENABLED', new_callable=PropertyMock)
    def test_check_local_authorized(self, mock_dataset_auth_status_check_enabled: MagicMock):
        with db.session_scope() as session:
            mock_dataset_auth_status_check_enabled.return_value = _Flag('dataset_auth_status_check_enabled', True)
            dataset_job = session.query(DatasetJob).get(1)
            auth_service = AuthService(session=session, dataset_job=dataset_job)
            self.assertTrue(auth_service.check_local_authorized())
            dataset_job.output_dataset.auth_status = AuthStatus.WITHDRAW
            self.assertFalse(auth_service.check_local_authorized())

            mock_dataset_auth_status_check_enabled.reset_mock()
            mock_dataset_auth_status_check_enabled.return_value = _Flag('dataset_auth_status_check_enabled', False)
            self.assertTrue(auth_service.check_local_authorized())

    @patch('fedlearner_webconsole.flag.models.Flag.DATASET_AUTH_STATUS_CHECK_ENABLED', new_callable=PropertyMock)
    def test_check_participants_authorized(self, mock_dataset_auth_status_check_enabled: MagicMock):
        participants_info = ParticipantsInfo(
            participants_map={
                'test-domain-name-coordinator': ParticipantInfo(auth_status='AUTHORIZED'),
                'test-domain-name-1': ParticipantInfo(auth_status='PENDING')
            })
        with db.session_scope() as session:
            mock_dataset_auth_status_check_enabled.return_value = _Flag('dataset_auth_status_check_enabled', True)
            dataset_job = session.query(DatasetJob).get(1)
            auth_service = AuthService(session=session, dataset_job=dataset_job)
            self.assertTrue(auth_service.check_participants_authorized())
            dataset_job.output_dataset.set_participants_info(participants_info)
            self.assertFalse(auth_service.check_participants_authorized())

            mock_dataset_auth_status_check_enabled.reset_mock()
            mock_dataset_auth_status_check_enabled.return_value = _Flag('dataset_auth_status_check_enabled', False)
            self.assertTrue(auth_service.check_participants_authorized())


if __name__ == '__main__':
    unittest.main()

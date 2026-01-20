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
from unittest.mock import patch
from testing.common import NoWebServerTestCase
from google.protobuf.text_format import MessageToString
from fedlearner_webconsole.db import db
from fedlearner_webconsole.tee.models import TrustedJobGroup, GroupCreateStatus, TrustedJob
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.algorithm.models import Algorithm, AlgorithmType
from fedlearner_webconsole.dataset.models import Dataset, DataBatch
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData, LaunchTrustedJobData
from fedlearner_webconsole.two_pc.trusted_job_launcher import TrustedJobLauncher
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.proto.tee_pb2 import Resource
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.participant.models import Participant


class TrustedJobLauncherTest(NoWebServerTestCase):

    def setUp(self) -> None:
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project-name')
            participant = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            algorithm = Algorithm(id=1,
                                  uuid='algorithm-uuid1',
                                  type=AlgorithmType.TRUSTED_COMPUTING,
                                  path='file:///data/algorithm/test/run.sh')
            dataset1 = Dataset(id=1, name='dataset-name1', uuid='dataset-uuid1', is_published=True)
            data_batch1 = DataBatch(id=1, dataset_id=1)
            dataset2 = Dataset(id=2, name='dataset-name2', uuid='dataset-uuid2', is_published=False)
            group = TrustedJobGroup(id=1,
                                    uuid='group-uuid',
                                    project_id=1,
                                    latest_version=1,
                                    coordinator_id=1,
                                    status=GroupCreateStatus.SUCCEEDED,
                                    auth_status=AuthStatus.AUTHORIZED,
                                    algorithm_uuid='algorithm-uuid1',
                                    dataset_id=1,
                                    resource=MessageToString(Resource(cpu=2, memory=2, replicas=1)))
            session.add_all([project, participant, algorithm, dataset1, data_batch1, dataset2, group])
            session.commit()

    @staticmethod
    def get_transaction_data(uuid: str, version: int, group_uuid: str, initiator_pure_domain_name: str):
        return TransactionData(launch_trusted_job_data=LaunchTrustedJobData(
            uuid=uuid, version=version, group_uuid=group_uuid, initiator_pure_domain_name=initiator_pure_domain_name))

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    def test_prepare(self, mock_get_system_info):
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='domain1')
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            # successful
            data = self.get_transaction_data('trusted-job-uuid', 2, 'group-uuid', 'domain2')
            launcher = TrustedJobLauncher(session, '13', data)
            flag, msg = launcher.prepare()
            self.assertTrue(flag)
            # fail due to initiator not found
            data = self.get_transaction_data('trusted-job-uuid', 2, 'group-uuid', 'domain3')
            launcher = TrustedJobLauncher(session, '13', data)
            flag, msg = launcher.prepare()
            self.assertFalse(flag)
            # fail due to group not found
            data = self.get_transaction_data('trusted-job-uuid', 2, 'not-exist', 'domain2')
            launcher = TrustedJobLauncher(session, '13', data)
            flag, msg = launcher.prepare()
            self.assertFalse(flag)
            # fail due to version conflict
            data = self.get_transaction_data('trusted-job-uuid', 1, 'group-uuid', 'domain2')
            launcher = TrustedJobLauncher(session, '13', data)
            flag, msg = launcher.prepare()
            self.assertFalse(flag)
            # fail due to auth
            group.auth_status = AuthStatus.PENDING
            data = self.get_transaction_data('trusted-job-uuid', 2, 'group-uuid', 'domain2')
            launcher = TrustedJobLauncher(session, '13', data)
            flag, msg = launcher.prepare()
            self.assertFalse(flag)
            # fail due to dataset unpublished
            group.auth_status = AuthStatus.AUTHORIZED
            group.dataset_id = 2
            data = self.get_transaction_data('trusted-job-uuid', 2, 'group-uuid', 'domain2')
            launcher = TrustedJobLauncher(session, '13', data)
            flag, msg = launcher.prepare()
            self.assertFalse(flag)
            # fail due to algorithm not found
            group.dataset_id = 1
            group.algorithm_uuid = 'algorithm-not-exist'
            data = self.get_transaction_data('trusted-job-uuid', 2, 'group-uuid', 'domain2')
            launcher = TrustedJobLauncher(session, '13', data)
            flag, msg = launcher.prepare()
            self.assertFalse(flag)

    @patch('fedlearner_webconsole.tee.services.get_batch_data_path')
    def test_commit(self, mock_get_batch_data_path):
        mock_get_batch_data_path.return_value = 'file:///data/test'
        with db.session_scope() as session:
            data = self.get_transaction_data('trusted-job-uuid', 2, 'group-uuid', 'domain2')
            launcher = TrustedJobLauncher(session, '13', data)
            flag, msg = launcher.commit()
            session.commit()
        self.assertTrue(flag)
        with db.session_scope() as session:
            trusted_job = session.query(TrustedJob).filter_by(trusted_job_group_id=1, version=2).first()
            self.assertIsNotNone(trusted_job)
            self.assertEqual(trusted_job.name, 'V2')
            self.assertEqual(trusted_job.coordinator_id, 1)
            group = session.query(TrustedJobGroup).get(1)
            self.assertEqual(group.latest_version, 2)


if __name__ == '__main__':
    unittest.main()

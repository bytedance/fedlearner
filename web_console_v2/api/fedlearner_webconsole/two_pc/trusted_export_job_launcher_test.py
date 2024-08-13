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
from google.protobuf.text_format import MessageToString
from fedlearner_webconsole.db import db
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.two_pc.trusted_export_job_launcher import TrustedExportJobLauncher
from fedlearner_webconsole.tee.models import TrustedJobGroup, TrustedJob, TrustedJobType, TrustedJobStatus
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.tee_pb2 import Resource
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData, LaunchTrustedExportJobData
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.job.models import Job, JobType, JobState


class TrustedExportJobLauncherTest(NoWebServerTestCase):

    def setUp(self) -> None:
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project-name')
            participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            proj_part1 = ProjectParticipant(project_id=1, participant_id=1)
            group = TrustedJobGroup(id=1, analyzer_id=0)
            tee_export_job = TrustedJob(id=1,
                                        uuid='uuid1',
                                        name='V1-domain1-1',
                                        type=TrustedJobType.EXPORT,
                                        version=1,
                                        project_id=1,
                                        trusted_job_group_id=1,
                                        auth_status=AuthStatus.AUTHORIZED,
                                        status=TrustedJobStatus.CREATED,
                                        export_count=1,
                                        coordinator_id=1,
                                        resource=MessageToString(Resource(cpu=1000, memory=1, replicas=1)))
            tee_analyze_job = TrustedJob(id=2,
                                         uuid='uuid2',
                                         type=TrustedJobType.ANALYZE,
                                         version=1,
                                         trusted_job_group_id=1,
                                         job_id=1,
                                         status=TrustedJobStatus.SUCCEEDED)
            job = Job(id=1,
                      name='trusted-job-1-uuid2',
                      job_type=JobType.CUSTOMIZED,
                      state=JobState.COMPLETED,
                      workflow_id=0,
                      project_id=1)
            sys_var = SettingService(session).get_system_variables_dict()
            session.add_all([project, participant1, proj_part1, group, tee_export_job, tee_analyze_job, job])
            session.commit()
        sys_var['sgx_image'] = 'artifact.bytedance.com/fedlearner/pp_bioinformatics:e13eb8a1d96ad046ca7354b8197d41fd'
        self.sys_var = sys_var

    @staticmethod
    def get_transaction_data(uuid: str):
        return TransactionData(launch_trusted_export_job_data=LaunchTrustedExportJobData(uuid=uuid))

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    def test_prepare(self, mock_get_system_info: MagicMock):
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='domain1')
        with db.session_scope() as session:
            tee_export_job = session.query(TrustedJob).get(1)
            # successful
            data = self.get_transaction_data('uuid1')
            launcher = TrustedExportJobLauncher(session, '13', data)
            flag, msg = launcher.prepare()
            self.assertTrue(flag)
            # fail due to tee_export_job not exist
            data = self.get_transaction_data('not-exist')
            launcher = TrustedExportJobLauncher(session, '13', data)
            flag, msg = launcher.prepare()
            self.assertFalse(flag)
            # fail due to auth
            tee_export_job.auth_status = AuthStatus.WITHDRAW
            data = self.get_transaction_data('uuid1')
            launcher = TrustedExportJobLauncher(session, '13', data)
            flag, msg = launcher.prepare()
            self.assertFalse(flag)

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_variables_dict')
    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    def test_commit(self, mock_get_system_info: MagicMock, mock_sys_dict: MagicMock):
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='domain1')
        mock_sys_dict.return_value = self.sys_var
        with db.session_scope() as session:
            data = self.get_transaction_data('uuid1')
            launcher = TrustedExportJobLauncher(session, '13', data)
            flag, msg = launcher.commit()
            self.assertTrue(flag)
            session.commit()
        with db.session_scope() as session:
            tee_export_job = session.query(TrustedJob).get(1)
            self.assertIsNotNone(tee_export_job.job_id)
            self.assertEqual(tee_export_job.get_status(), TrustedJobStatus.PENDING)


if __name__ == '__main__':
    unittest.main()

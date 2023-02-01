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
from google.protobuf.empty_pb2 import Empty
from google.protobuf.text_format import MessageToString
from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.dataset.models import Dataset, DataBatch
from fedlearner_webconsole.algorithm.models import Algorithm, AlgorithmProject, AlgorithmType
from fedlearner_webconsole.tee.models import TrustedJobGroup, GroupCreateStatus, TrustedJob, TrustedJobType, \
    TrustedJobStatus
from fedlearner_webconsole.tee.runners import TeeCreateRunner, TeeResourceCheckRunner
from fedlearner_webconsole.proto.tee_pb2 import ParticipantDatasetList, ParticipantDataset, Resource
from fedlearner_webconsole.proto.rpc.v2.job_service_pb2 import GetTrustedJobGroupResponse
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.review.common import NO_CENTRAL_SERVER_UUID


class TeeRunnerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            participant2 = Participant(id=2, name='part3', domain_name='fl-domain3.com')
            proj_part1 = ProjectParticipant(project_id=1, participant_id=1)
            proj_part2 = ProjectParticipant(project_id=1, participant_id=2)
            dataset1 = Dataset(id=1, name='dataset-name1', uuid='dataset-uuid1', is_published=True)
            data_batch1 = DataBatch(id=1, dataset_id=1)
            dataset2 = Dataset(id=2, name='dataset-name2', uuid='dataset-uuid2', is_published=False)
            algorithm = Algorithm(id=1,
                                  uuid='algorithm-uuid1',
                                  type=AlgorithmType.TRUSTED_COMPUTING,
                                  algorithm_project_id=1)
            algorithm_proj = AlgorithmProject(id=1, uuid='algorithm-proj-uuid')
            session.add_all([
                project, participant1, proj_part1, participant2, proj_part2, dataset1, data_batch1, dataset2, algorithm,
                algorithm_proj
            ])
            session.commit()

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager._remote_do_two_pc')
    def test_create_trusted_job_group(self, mock_remote_do_two_pc, mock_get_system_info):
        mock_remote_do_two_pc.return_value = True, ''
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='domain1')
        with db.session_scope() as session:
            participant_datasets = ParticipantDatasetList(
                items=[ParticipantDataset(participant_id=1, uuid='dataset-uuid3', name='dataset-name3')])
            # group in ticket_status APPROVED / status PENDING / valid params
            group1 = TrustedJobGroup(id=1,
                                     project_id=1,
                                     ticket_status=TicketStatus.APPROVED,
                                     ticket_uuid=NO_CENTRAL_SERVER_UUID,
                                     algorithm_uuid='algorithm-uuid1',
                                     dataset_id=1,
                                     coordinator_id=0,
                                     analyzer_id=1,
                                     uuid='uuid1')
            group1.set_participant_datasets(participant_datasets)
            # group in ticket_status APPROVED / status PENDING / invalid params
            # error at controller run
            group2 = TrustedJobGroup(id=2,
                                     project_id=10,
                                     ticket_status=TicketStatus.APPROVED,
                                     ticket_uuid=NO_CENTRAL_SERVER_UUID,
                                     algorithm_uuid='algorithm-uuid2',
                                     dataset_id=1,
                                     coordinator_id=0,
                                     analyzer_id=0,
                                     uuid='uuid2')
            # error at prepare
            group3 = TrustedJobGroup(id=3,
                                     project_id=1,
                                     ticket_status=TicketStatus.APPROVED,
                                     ticket_uuid=NO_CENTRAL_SERVER_UUID,
                                     algorithm_uuid='algorithm-uuid1',
                                     dataset_id=2,
                                     coordinator_id=0,
                                     analyzer_id=0,
                                     uuid='uuid3')
            # status FAILED
            group4 = TrustedJobGroup(id=4,
                                     project_id=1,
                                     ticket_status=TicketStatus.APPROVED,
                                     ticket_uuid=NO_CENTRAL_SERVER_UUID,
                                     algorithm_uuid='algorithm-uuid1',
                                     dataset_id=1,
                                     coordinator_id=0,
                                     analyzer_id=0,
                                     status=GroupCreateStatus.FAILED,
                                     uuid='uuid4')
            # status SUCCEEDED
            group5 = TrustedJobGroup(id=5,
                                     project_id=1,
                                     ticket_status=TicketStatus.APPROVED,
                                     ticket_uuid=NO_CENTRAL_SERVER_UUID,
                                     algorithm_uuid='algorithm-uuid1',
                                     dataset_id=1,
                                     coordinator_id=0,
                                     analyzer_id=0,
                                     status=GroupCreateStatus.SUCCEEDED,
                                     uuid='uuid5')
            session.add_all([group1, group2, group3, group4, group5])
            session.commit()
        runner = TeeCreateRunner()
        # first run
        # pylint: disable=protected-access
        processed_groups = runner._create_trusted_job_group()
        self.assertEqual(processed_groups, set([1, 2, 3]))
        with db.session_scope() as session:
            group1: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            self.assertEqual(group1.status, GroupCreateStatus.SUCCEEDED)
            group2: TrustedJobGroup = session.query(TrustedJobGroup).get(2)
            self.assertEqual(group2.status, GroupCreateStatus.FAILED)
            group3: TrustedJobGroup = session.query(TrustedJobGroup).get(3)
            self.assertEqual(group3.status, GroupCreateStatus.FAILED)
        # second run should do nothing
        processed_groups = runner._create_trusted_job_group()
        self.assertEqual(processed_groups, set())

    @patch('fedlearner_webconsole.tee.services.get_batch_data_path')
    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager._remote_do_two_pc')
    def test_launch_trusted_job(self, mock_remote_do_two_pc, mock_get_system_info, mock_get_batch_data_path):
        mock_remote_do_two_pc.return_value = True, ''
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='domain1')
        mock_get_batch_data_path.return_value = 'file:///data/test'
        with db.session_scope() as session:
            # valid
            group1 = TrustedJobGroup(id=1,
                                     project_id=1,
                                     uuid='uuid1',
                                     status=GroupCreateStatus.SUCCEEDED,
                                     coordinator_id=0,
                                     latest_version=0,
                                     algorithm_uuid='algorithm-uuid1',
                                     dataset_id=1,
                                     auth_status=AuthStatus.AUTHORIZED,
                                     resource=MessageToString(Resource(cpu=1000, memory=1, replicas=1)))
            # not fully authorized
            group2 = TrustedJobGroup(id=2,
                                     project_id=1,
                                     uuid='uuid2',
                                     status=GroupCreateStatus.SUCCEEDED,
                                     coordinator_id=0,
                                     latest_version=0,
                                     algorithm_uuid='algorithm-uuid1',
                                     auth_status=AuthStatus.AUTHORIZED,
                                     unauth_participant_ids='1,2')
            # not creator
            group3 = TrustedJobGroup(id=3,
                                     project_id=1,
                                     uuid='uuid3',
                                     status=GroupCreateStatus.SUCCEEDED,
                                     coordinator_id=1,
                                     latest_version=0,
                                     algorithm_uuid='algorithm-uuid1',
                                     auth_status=AuthStatus.AUTHORIZED)
            session.add_all([group1, group2, group3])
            session.commit()
        runner = TeeCreateRunner()
        # first run
        # pylint: disable=protected-access
        processed_groups = runner._launch_trusted_job()
        self.assertCountEqual(processed_groups, [1])
        with db.session_scope() as session:
            group1: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            self.assertEqual(group1.latest_version, 1)
            trusted_job: TrustedJob = session.query(TrustedJob).filter_by(trusted_job_group_id=1, version=1).first()
            self.assertIsNotNone(trusted_job)
            self.assertEqual(group2.latest_version, 0)
            self.assertEqual(group3.latest_version, 0)
        # second run
        processed_groups = runner._launch_trusted_job()
        self.assertEqual(processed_groups, set())

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.get_trusted_job_group')
    def test_update_unauth_participant_ids(self, mock_client: MagicMock):
        with db.session_scope() as session:
            group1 = TrustedJobGroup(id=1,
                                     uuid='uuid1',
                                     project_id=1,
                                     unauth_participant_ids='1,2',
                                     status=GroupCreateStatus.SUCCEEDED)
            group2 = TrustedJobGroup(id=2,
                                     uuid='uuid2',
                                     project_id=1,
                                     unauth_participant_ids='2',
                                     status=GroupCreateStatus.SUCCEEDED)
            group3 = TrustedJobGroup(id=3,
                                     uuid='uuid3',
                                     project_id=1,
                                     unauth_participant_ids='1,2',
                                     status=GroupCreateStatus.FAILED)
            session.add_all([group1, group2, group3])
            session.commit()
        # for 2 participants and 2 valid groups, client should be called 4 times
        # pylint: disable=protected-access
        mock_client.side_effect = [
            GetTrustedJobGroupResponse(auth_status='PENDING'),
            GetTrustedJobGroupResponse(auth_status='AUTHORIZED'),
            GetTrustedJobGroupResponse(auth_status='AUTHORIZED'),
            GetTrustedJobGroupResponse(auth_status='AUTHORIZED')
        ]
        runner = TeeResourceCheckRunner()
        processed_groups = runner._update_unauth_participant_ids()
        self.assertCountEqual(processed_groups, [1, 2])
        with db.session_scope() as session:
            group1: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            self.assertCountEqual(group1.get_unauth_participant_ids(), [1])
            group2: TrustedJobGroup = session.query(TrustedJobGroup).get(2)
            self.assertCountEqual(group2.get_unauth_participant_ids(), [])

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.create_trusted_export_job')
    def test_create_trusted_export_job(self, mock_client: MagicMock):
        mock_client.return_value = Empty()
        with db.session_scope() as session:
            tee_analyze_job = TrustedJob(id=1,
                                         uuid='uuid1',
                                         type=TrustedJobType.ANALYZE,
                                         project_id=1,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=2,
                                         status=TrustedJobStatus.SUCCEEDED)
            tee_export_job1 = TrustedJob(id=2,
                                         uuid='uuid2',
                                         type=TrustedJobType.EXPORT,
                                         project_id=1,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=1,
                                         ticket_status=TicketStatus.APPROVED,
                                         status=TrustedJobStatus.NEW)
            tee_export_job2 = TrustedJob(id=3,
                                         uuid='uuid3',
                                         type=TrustedJobType.EXPORT,
                                         project_id=1,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=2,
                                         ticket_status=TicketStatus.APPROVED,
                                         status=TrustedJobStatus.NEW)
            tee_export_job3 = TrustedJob(id=4,
                                         uuid='uuid4',
                                         type=TrustedJobType.EXPORT,
                                         project_id=1,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=1,
                                         ticket_status=TicketStatus.APPROVED,
                                         status=TrustedJobStatus.CREATED)
            tee_export_job4 = TrustedJob(id=5,
                                         uuid='uuid5',
                                         type=TrustedJobType.EXPORT,
                                         project_id=1,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=3,
                                         ticket_status=TicketStatus.PENDING,
                                         status=TrustedJobStatus.NEW)
            session.add_all([tee_analyze_job, tee_export_job1, tee_export_job2, tee_export_job3, tee_export_job4])
            session.commit()
        runner = TeeCreateRunner()
        # pylint: disable=protected-access
        processed_ids = runner._create_trusted_export_job()
        self.assertCountEqual(processed_ids, [2, 3])
        with db.session_scope() as session:
            tee_export_job1 = session.query(TrustedJob).get(2)
            self.assertEqual(tee_export_job1.status, TrustedJobStatus.CREATED)
            tee_export_job2 = session.query(TrustedJob).get(3)
            self.assertEqual(tee_export_job2.status, TrustedJobStatus.CREATED)

    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager.run')
    def test_launch_trusted_export_job(self, mock_run):
        mock_run.return_value = True, ''
        with db.session_scope() as session:
            tee_export_job1 = TrustedJob(id=1,
                                         type=TrustedJobType.EXPORT,
                                         project_id=1,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=1,
                                         ticket_status=TicketStatus.APPROVED,
                                         status=TrustedJobStatus.CREATED,
                                         coordinator_id=0)
            tee_export_job2 = TrustedJob(id=2,
                                         type=TrustedJobType.EXPORT,
                                         project_id=1,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=2,
                                         ticket_status=TicketStatus.APPROVED,
                                         status=TrustedJobStatus.CREATED,
                                         coordinator_id=0)
            participants_info = tee_export_job2.get_participants_info()
            participants_info.participants_map['domain1'].auth_status = 'WITHDRAW'
            tee_export_job2.set_participants_info(participants_info)
            tee_export_job3 = TrustedJob(id=3,
                                         type=TrustedJobType.EXPORT,
                                         project_id=1,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=3,
                                         ticket_status=TicketStatus.APPROVED,
                                         status=TrustedJobStatus.CREATED,
                                         coordinator_id=1)
            tee_export_job4 = TrustedJob(id=4,
                                         type=TrustedJobType.EXPORT,
                                         project_id=1,
                                         version=2,
                                         trusted_job_group_id=1,
                                         export_count=1,
                                         ticket_status=TicketStatus.APPROVED,
                                         status=TrustedJobStatus.NEW,
                                         coordinator_id=0)
            session.add_all([tee_export_job1, tee_export_job2, tee_export_job3, tee_export_job4])
            session.commit()
        runner = TeeCreateRunner()
        # pylint: disable=protected-access
        processed_ids = runner._launch_trusted_export_job()
        self.assertCountEqual(processed_ids, [1])

    def test_create_export_dataset(self):
        with db.session_scope() as session:
            group1 = TrustedJobGroup(id=1, name='group1', project_id=1, uuid='group-uuid1')
            tee_export_job1 = TrustedJob(id=1,
                                         name='V1-me-1',
                                         type=TrustedJobType.EXPORT,
                                         project_id=1,
                                         job_id=1,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=1,
                                         status=TrustedJobStatus.SUCCEEDED,
                                         coordinator_id=0)
            tee_export_job2 = TrustedJob(id=2,
                                         type=TrustedJobType.EXPORT,
                                         project_id=1,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=2,
                                         status=TrustedJobStatus.RUNNING,
                                         coordinator_id=0)
            tee_export_job3 = TrustedJob(id=3,
                                         type=TrustedJobType.EXPORT,
                                         project_id=1,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=3,
                                         status=TrustedJobStatus.SUCCEEDED,
                                         coordinator_id=1)
            tee_export_job4 = TrustedJob(id=4,
                                         type=TrustedJobType.EXPORT,
                                         project_id=1,
                                         version=2,
                                         trusted_job_group_id=1,
                                         export_count=1,
                                         status=TrustedJobStatus.SUCCEEDED,
                                         coordinator_id=0,
                                         export_dataset_id=1)
            job1 = Job(id=1,
                       name='job-name1',
                       job_type=JobType.CUSTOMIZED,
                       workflow_id=0,
                       project_id=1,
                       state=JobState.COMPLETED)
            session.add_all([group1, tee_export_job1, tee_export_job2, tee_export_job3, tee_export_job4, job1])
            session.commit()
        runner = TeeCreateRunner()
        # pylint: disable=protected-access
        processed_ids = runner._create_export_dataset()
        self.assertCountEqual(processed_ids, [1])
        with db.session_scope() as session:
            tee_export_job1 = session.query(TrustedJob).get(1)
            dataset = session.query(Dataset).get(tee_export_job1.export_dataset_id)
            self.assertEqual(dataset.name, 'group1-V1-me-1')
            self.assertEqual(len(dataset.data_batches), 1)


if __name__ == '__main__':
    unittest.main()

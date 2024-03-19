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
from typing import List
import grpc
from google.protobuf.text_format import MessageToString
from testing.no_web_server_test_case import NoWebServerTestCase
from testing.rpc.client import FakeRpcError
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.algorithm.models import AlgorithmProject, Algorithm, AlgorithmType
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData, CreateTrustedJobGroupData
from fedlearner_webconsole.proto.tee_pb2 import DomainNameDataset, ParticipantDataset, ParticipantDatasetList
from fedlearner_webconsole.tee.models import TrustedJobGroup, GroupCreateStatus
from fedlearner_webconsole.two_pc.trusted_job_group_creator import TrustedJobGroupCreator
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.review.common import NO_CENTRAL_SERVER_UUID


class TrustedJobGroupCreatorTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        project = Project(id=1, name='project')
        participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
        participant2 = Participant(id=2, name='part3', domain_name='fl-domain3.com')
        proj_part1 = ProjectParticipant(project_id=1, participant_id=1)
        proj_part2 = ProjectParticipant(project_id=1, participant_id=2)
        dataset1 = Dataset(id=1, name='dataset-name1', uuid='dataset-uuid1', is_published=True)
        dataset2 = Dataset(id=2, name='dataset-name3', uuid='dataset-uuid3', is_published=False)
        algorithm_proj1 = AlgorithmProject(id=1, uuid='algorithm-proj-uuid1', type=AlgorithmType.TRUSTED_COMPUTING)
        algorithm1 = Algorithm(id=1,
                               uuid='algorithm-uuid1',
                               type=AlgorithmType.TRUSTED_COMPUTING,
                               algorithm_project_id=1)
        algorithm2 = Algorithm(id=2, uuid='algorithm-uuid2', algorithm_project_id=1)
        with db.session_scope() as session:
            session.add_all([
                project,
                participant1,
                participant2,
                proj_part1,
                proj_part2,
                dataset1,
                dataset2,
                algorithm1,
                algorithm2,
                algorithm_proj1,
            ])
            session.commit()

    @staticmethod
    def get_transaction_data(name: str, uuid: str, ticket_uuid: str, project_name: str, algorithm_project_uuid: str,
                             algorithm_uuid: str, domain_name_datasets: List[DomainNameDataset],
                             coordinator_pure_domain_name: str, analyzer_pure_domain_name: str):
        return TransactionData(create_trusted_job_group_data=CreateTrustedJobGroupData(
            name=name,
            uuid=uuid,
            ticket_uuid=ticket_uuid,
            project_name=project_name,
            algorithm_project_uuid=algorithm_project_uuid,
            algorithm_uuid=algorithm_uuid,
            domain_name_datasets=domain_name_datasets,
            coordinator_pure_domain_name=coordinator_pure_domain_name,
            analyzer_pure_domain_name=analyzer_pure_domain_name,
        ))

    @patch('fedlearner_webconsole.algorithm.fetcher.AlgorithmFetcher.get_algorithm_from_participant')
    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    def test_prepare(self, mock_get_system_info, mock_get_algorithm):
        # successful case
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='domain1')
        mock_get_algorithm.side_effect = FakeRpcError(grpc.StatusCode.NOT_FOUND, 'not found')
        data = self.get_transaction_data(
            'group-name',
            'group-uuid',
            NO_CENTRAL_SERVER_UUID,
            'project',
            'algorithm-proj-uuid1',
            'algorithm-uuid1',
            [
                DomainNameDataset(
                    pure_domain_name='domain1', dataset_uuid='dataset-uuid1', dataset_name='dataset-name1'),
                DomainNameDataset(
                    pure_domain_name='domain2', dataset_uuid='dataset-uuid2', dataset_name='dataset-name2'),
            ],
            'domain2',
            'domain2',
        )
        with db.session_scope() as session:
            creator = TrustedJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertTrue(flag)
        # fail due to algorithm not found
        data.create_trusted_job_group_data.algorithm_uuid = 'algorithm-not-exist'
        with db.session_scope() as session:
            creator = TrustedJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertFalse(flag)
        # fail due to algorithm type invalid
        data.create_trusted_job_group_data.algorithm_uuid = 'algorithm-uuid2'
        with db.session_scope() as session:
            creator = TrustedJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertFalse(flag)
        # fail due to participant not found
        data = self.get_transaction_data(
            'group-name',
            'group-uuid',
            NO_CENTRAL_SERVER_UUID,
            'project',
            'algorithm-proj-uuid1',
            'algorithm-uuid1',
            [
                DomainNameDataset(
                    pure_domain_name='domain1', dataset_uuid='dataset-uuid1', dataset_name='dataset-name1'),
                DomainNameDataset(
                    pure_domain_name='domain-not-exist', dataset_uuid='dataset-uuid2', dataset_name='dataset-name2'),
            ],
            'domain2',
            'domain2',
        )
        with db.session_scope() as session:
            creator = TrustedJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertFalse(flag)
        # fail due to dataset not found
        data = self.get_transaction_data(
            'group-name',
            'group-uuid',
            NO_CENTRAL_SERVER_UUID,
            'project',
            'algorithm-proj-uuid1',
            'algorithm-uuid1',
            [
                DomainNameDataset(
                    pure_domain_name='domain1', dataset_uuid='dataset-uuid-not-exist', dataset_name='dataset-name1'),
                DomainNameDataset(
                    pure_domain_name='domain2', dataset_uuid='dataset-uuid2', dataset_name='dataset-name2'),
            ],
            'domain2',
            'domain2',
        )
        with db.session_scope() as session:
            creator = TrustedJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertFalse(flag)
        # fail due to dataset not published
        data = self.get_transaction_data(
            'group-name',
            'group-uuid',
            NO_CENTRAL_SERVER_UUID,
            'project',
            'algorithm-proj-uuid1',
            'algorithm-uuid1',
            [
                DomainNameDataset(
                    pure_domain_name='domain1', dataset_uuid='dataset-uuid3', dataset_name='dataset-name3'),
                DomainNameDataset(
                    pure_domain_name='domain2', dataset_uuid='dataset-uuid2', dataset_name='dataset-name2'),
            ],
            'domain2',
            'domain2',
        )
        with db.session_scope() as session:
            creator = TrustedJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertFalse(flag)
        # fail due to same trusted job group name with different uuid in project
        with db.session_scope() as session:
            group = TrustedJobGroup(name='group-name', uuid='other-group-uuid', project_id=1)
            session.add(group)
            session.commit()
        with db.session_scope() as session:
            creator = TrustedJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertFalse(flag)

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    def test_commit(self, mock_get_system_info):
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='domain1')
        data = self.get_transaction_data(
            'group-name',
            'group-uuid',
            NO_CENTRAL_SERVER_UUID,
            'project',
            'algorithm-proj-uuid1',
            'algorithm-uuid1',
            [
                DomainNameDataset(
                    pure_domain_name='domain1', dataset_uuid='dataset-uuid1', dataset_name='dataset-name1'),
                DomainNameDataset(
                    pure_domain_name='domain2', dataset_uuid='dataset-uuid2', dataset_name='dataset-name2'),
            ],
            'domain2',
            'domain2',
        )
        with db.session_scope() as session:
            creator = TrustedJobGroupCreator(session, '12', data)
            flag, msg = creator.commit()
            session.commit()
            self.assertTrue(flag)
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).filter_by(name='group-name').first()
            self.assertEqual(group.uuid, 'group-uuid')
            self.assertEqual(group.latest_version, 0)
            self.assertEqual(group.project_id, 1)
            self.assertEqual(group.coordinator_id, 1)
            self.assertEqual(group.analyzer_id, 1)
            self.assertEqual(group.ticket_uuid, NO_CENTRAL_SERVER_UUID)
            self.assertEqual(group.ticket_status, TicketStatus.APPROVED)
            self.assertEqual(group.status, GroupCreateStatus.SUCCEEDED)
            self.assertEqual(group.auth_status, AuthStatus.PENDING)
            self.assertEqual(group.unauth_participant_ids, '2')
            self.assertEqual(group.algorithm_uuid, 'algorithm-uuid1')
            self.assertEqual(group.dataset_id, 1)
            participant_datasets = ParticipantDatasetList(
                items=[ParticipantDataset(
                    participant_id=1,
                    uuid='dataset-uuid2',
                    name='dataset-name2',
                )])
            self.assertEqual(group.participant_datasets, MessageToString(participant_datasets))


if __name__ == '__main__':
    unittest.main()

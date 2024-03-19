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
import grpc
from testing.no_web_server_test_case import NoWebServerTestCase
from testing.rpc.client import FakeRpcError
from google.protobuf.empty_pb2 import Empty
from google.protobuf.text_format import MessageToString
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.tee.models import TrustedJobGroup, TrustedJob, TrustedJobType, TrustedJobStatus
from fedlearner_webconsole.tee.controller import TrustedJobGroupController, TrustedJobController
from fedlearner_webconsole.proto.rpc.v2.job_service_pb2 import GetTrustedJobGroupResponse
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.exceptions import InternalException
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus


class TrustedJobGroupControllerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            participant2 = Participant(id=2, name='part3', domain_name='fl-domain3.com')
            proj_part1 = ProjectParticipant(project_id=1, participant_id=1)
            proj_part2 = ProjectParticipant(project_id=1, participant_id=2)
            group = TrustedJobGroup(id=1, uuid='uuid', auth_status=AuthStatus.AUTHORIZED, unauth_participant_ids='1,2')
            session.add_all([project, participant1, participant2, proj_part1, proj_part2, group])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.inform_trusted_job_group')
    def test_inform_trusted_job_group(self, mock_client: MagicMock):
        mock_client.return_value = Empty()
        with db.session_scope() as session:
            group = session.query(TrustedJobGroup).get(1)
            TrustedJobGroupController(session, 1).inform_trusted_job_group(group, AuthStatus.AUTHORIZED)
            self.assertEqual(group.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(mock_client.call_args_list, [(('uuid', AuthStatus.AUTHORIZED),),
                                                          (('uuid', AuthStatus.AUTHORIZED),)])
        # grpc abort with error
        mock_client.side_effect = FakeRpcError(grpc.StatusCode.NOT_FOUND, 'trusted job group request.uuid not found')
        with db.session_scope() as session:
            group = session.query(TrustedJobGroup).get(1)
            TrustedJobGroupController(session, 1).inform_trusted_job_group(group, AuthStatus.AUTHORIZED)
            self.assertEqual(group.auth_status, AuthStatus.AUTHORIZED)

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.update_trusted_job_group')
    def test_update_trusted_job_group(self, mock_client: MagicMock):
        mock_client.return_value = Empty()
        with db.session_scope() as session:
            group = session.query(TrustedJobGroup).get(1)
            TrustedJobGroupController(session, 1).update_trusted_job_group(group, 'algorithm-uuid')
            self.assertEqual(group.algorithm_uuid, 'algorithm-uuid')
            self.assertEqual(mock_client.call_args_list, [(('uuid', 'algorithm-uuid'),), (('uuid', 'algorithm-uuid'),)])
        # grpc abort with error
        mock_client.side_effect = FakeRpcError(grpc.StatusCode.INVALID_ARGUMENT, 'mismatched algorithm project')
        with self.assertRaises(InternalException):
            with db.session_scope() as session:
                group = session.query(TrustedJobGroup).get(1)
                TrustedJobGroupController(session, 1).update_trusted_job_group(group, 'algorithm-uuid')

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.delete_trusted_job_group')
    def test_delete_trusted_job_group(self, mock_client: MagicMock):
        mock_client.return_value = Empty()
        with db.session_scope() as session:
            group = session.query(TrustedJobGroup).get(1)
            TrustedJobGroupController(session, 1).delete_trusted_job_group(group)
            self.assertEqual(mock_client.call_args_list, [(('uuid',),), (('uuid',),)])
        # grpc abort with err
        mock_client.side_effect = FakeRpcError(grpc.StatusCode.INVALID_ARGUMENT, 'trusted job is not deletable')
        with self.assertRaises(InternalException):
            with db.session_scope() as session:
                group = session.query(TrustedJobGroup).get(1)
                TrustedJobGroupController(session, 1).delete_trusted_job_group(group)

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.get_trusted_job_group')
    def test_update_unauth_participant_ids(self, mock_client: MagicMock):
        mock_client.side_effect = [
            GetTrustedJobGroupResponse(auth_status='PENDING'),
            GetTrustedJobGroupResponse(auth_status='AUTHORIZED')
        ]
        with db.session_scope() as session:
            group = session.query(TrustedJobGroup).get(1)
            TrustedJobGroupController(session, 1).update_unauth_participant_ids(group)
            self.assertCountEqual(group.get_unauth_participant_ids(), [1])
        # grpc abort with err
        mock_client.side_effect = FakeRpcError(grpc.StatusCode.NOT_FOUND, 'trusted job group uuid not found')
        with db.session_scope() as session:
            group = session.query(TrustedJobGroup).get(1)
            TrustedJobGroupController(session, 1).update_unauth_participant_ids(group)
            self.assertCountEqual(group.get_unauth_participant_ids(), [1, 2])


class TrustedJobControllerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            participant2 = Participant(id=2, name='part3', domain_name='fl-domain3.com')
            proj_part1 = ProjectParticipant(project_id=1, participant_id=1)
            proj_part2 = ProjectParticipant(project_id=1, participant_id=2)
            participants_info = ParticipantsInfo()
            participants_info.participants_map['domain1'].auth_status = AuthStatus.PENDING.name
            participants_info.participants_map['domain2'].auth_status = AuthStatus.PENDING.name
            participants_info.participants_map['domain3'].auth_status = AuthStatus.WITHDRAW.name
            tee_export_job = TrustedJob(id=1,
                                        uuid='uuid1',
                                        name='V1-domain1-1',
                                        type=TrustedJobType.EXPORT,
                                        version=1,
                                        trusted_job_group_id=1,
                                        ticket_status=TicketStatus.APPROVED,
                                        ticket_uuid='ticket-uuid',
                                        auth_status=AuthStatus.PENDING,
                                        status=TrustedJobStatus.NEW,
                                        export_count=1,
                                        participants_info=MessageToString(participants_info))
            tee_analyze_job = TrustedJob(id=2,
                                         uuid='uuid2',
                                         type=TrustedJobType.ANALYZE,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=1,
                                         status=TrustedJobStatus.SUCCEEDED)
            session.add_all(
                [project, participant1, participant2, proj_part1, proj_part2, tee_export_job, tee_analyze_job])
            session.commit()

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.inform_trusted_job')
    def test_inform_auth_status(self, mock_client: MagicMock, mock_get_system_info: MagicMock):
        mock_client.return_value = Empty()
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='domain1')
        with db.session_scope() as session:
            trusted_job = session.query(TrustedJob).get(1)
            TrustedJobController(session, 1).inform_auth_status(trusted_job, AuthStatus.AUTHORIZED)
            self.assertEqual(trusted_job.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(trusted_job.get_participants_info().participants_map['domain1'].auth_status, 'AUTHORIZED')
            self.assertEqual(mock_client.call_args_list, [(('uuid1', AuthStatus.AUTHORIZED),),
                                                          (('uuid1', AuthStatus.AUTHORIZED),)])
        # grpc abort with error
        mock_client.side_effect = FakeRpcError(grpc.StatusCode.NOT_FOUND, 'not found')
        with db.session_scope() as session:
            group = session.query(TrustedJob).get(1)
            TrustedJobController(session, 1).inform_auth_status(group, AuthStatus.AUTHORIZED)
            self.assertEqual(group.auth_status, AuthStatus.AUTHORIZED)

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.get_trusted_job')
    def test_update_participants_info(self, mock_client: MagicMock):
        mock_client.side_effect = [
            GetTrustedJobGroupResponse(auth_status='WITHDRAW'),
            GetTrustedJobGroupResponse(auth_status='AUTHORIZED')
        ]
        with db.session_scope() as session:
            trusted_job = session.query(TrustedJob).get(1)
            TrustedJobController(session, 1).update_participants_info(trusted_job)
            self.assertEqual(trusted_job.get_participants_info().participants_map['domain2'].auth_status, 'WITHDRAW')
            self.assertEqual(trusted_job.get_participants_info().participants_map['domain3'].auth_status, 'AUTHORIZED')

        # grpc abort with err
        mock_client.side_effect = [
            FakeRpcError(grpc.StatusCode.NOT_FOUND, 'trusted job uuid not found'),
            GetTrustedJobGroupResponse(auth_status='AUTHORIZED')
        ]
        with db.session_scope() as session:
            trusted_job = session.query(TrustedJob).get(1)
            TrustedJobController(session, 1).update_participants_info(trusted_job)
            self.assertEqual(trusted_job.get_participants_info().participants_map['domain2'].auth_status, 'PENDING')
            self.assertEqual(trusted_job.get_participants_info().participants_map['domain3'].auth_status, 'AUTHORIZED')

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.create_trusted_export_job')
    def test_create_trusted_export_job(self, mock_client: MagicMock):
        mock_client.return_value = Empty()
        with db.session_scope() as session:
            tee_export_job = session.query(TrustedJob).get(1)
            tee_analyze_job = session.query(TrustedJob).get(2)
            TrustedJobController(session, 1).create_trusted_export_job(tee_export_job, tee_analyze_job)
            self.assertEqual(mock_client.call_args_list, [(('uuid1', 'V1-domain1-1', 1, 'uuid2', 'ticket-uuid'),)] * 2)
        # grpc abort with err
        mock_client.side_effect = [
            FakeRpcError(grpc.StatusCode.INVALID_ARGUMENT, 'tee_analyze_job uuid2 invalid'),
            Empty()
        ]
        with self.assertRaises(InternalException):
            with db.session_scope() as session:
                tee_export_job = session.query(TrustedJob).get(1)
                tee_analyze_job = session.query(TrustedJob).get(2)
                TrustedJobController(session, 1).create_trusted_export_job(tee_export_job, tee_analyze_job)


if __name__ == '__main__':
    unittest.main()

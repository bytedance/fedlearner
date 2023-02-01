# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
# pylint: disable=protected-access
import unittest
from unittest import mock
from unittest.mock import patch, MagicMock, call

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.proto.service_pb2 import TwoPcResponse
from fedlearner_webconsole.proto.two_pc_pb2 import TwoPcType, TwoPcAction, TransactionData, \
    CreateModelJobData
from fedlearner_webconsole.two_pc.transaction_manager import TransactionManager


class TransactionManagerTest(NoWebServerTestCase):
    _PROJECT_NAME = 'test-project'
    _PROJECT_TOKEN = 'testtoken'

    @patch('fedlearner_webconsole.two_pc.transaction_manager.RpcClient.from_project_and_participant')
    def test_init(self, mock_rpc_client_factory):
        mock_rpc_client_factory.return_value = MagicMock()
        tm = TransactionManager(project_name=self._PROJECT_NAME,
                                project_token=self._PROJECT_TOKEN,
                                two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                                participants=['fl1.com', 'fl2.com'])
        self.assertEqual(tm.type, TwoPcType.CREATE_MODEL_JOB)
        self.assertEqual(len(tm._clients), 2)

        calls = [
            call(project_name=self._PROJECT_NAME, project_token=self._PROJECT_TOKEN, domain_name='fl1.com'),
            call(project_name=self._PROJECT_NAME, project_token=self._PROJECT_TOKEN, domain_name='fl2.com')
        ]
        mock_rpc_client_factory.assert_has_calls(calls)

    @patch('fedlearner_webconsole.two_pc.transaction_manager.run_two_pc_action')
    @patch('fedlearner_webconsole.two_pc.transaction_manager.uuid4')
    def test_run(self, mock_uuid4, mock_local_run_two_pc_action):
        tid = 'testttttt'
        transaction_data = TransactionData(create_model_job_data=CreateModelJobData(model_job_name='test model name'))
        mock_uuid4.return_value = tid
        # Two participants
        p1 = MagicMock()
        p1.run_two_pc = MagicMock()
        p2 = MagicMock()
        p2.run_two_pc = MagicMock()
        # A hack to avoid mocking RpcClient.from_project_and_participant
        tm = TransactionManager(project_name=self._PROJECT_NAME,
                                project_token=self._PROJECT_TOKEN,
                                two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                                participants=[])
        tm._clients = [p1, p2]

        # Test successfully
        p1.run_two_pc.return_value = TwoPcResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                   succeeded=True)
        p2.run_two_pc.return_value = TwoPcResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                   succeeded=True)
        mock_local_run_two_pc_action.return_value = (True, '')
        succeeded, _ = tm.run(transaction_data)
        self.assertTrue(succeeded)
        mock_uuid4.assert_called_once()
        calls = [
            call(transaction_uuid=tid,
                 two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                 action=TwoPcAction.PREPARE,
                 data=transaction_data),
            call(transaction_uuid=tid,
                 two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                 action=TwoPcAction.COMMIT,
                 data=transaction_data),
        ]
        p1.run_two_pc.assert_has_calls(calls)
        p2.run_two_pc.assert_has_calls(calls)
        mock_local_run_two_pc_action.assert_has_calls([
            call(session=mock.ANY,
                 tid=tid,
                 two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                 action=TwoPcAction.PREPARE,
                 data=transaction_data),
            call(session=mock.ANY,
                 tid=tid,
                 two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                 action=TwoPcAction.COMMIT,
                 data=transaction_data),
        ])

        # Test failed
        def p2_run_two_pc(action: TwoPcAction, *args, **kwargs) -> TwoPcResponse:
            if action == TwoPcAction.PREPARE:
                return TwoPcResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS), succeeded=False)
            return TwoPcResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS), succeeded=True)

        p2.run_two_pc.side_effect = p2_run_two_pc
        mock_uuid4.reset_mock()
        succeeded, _ = tm.run(transaction_data)
        self.assertFalse(succeeded)
        mock_uuid4.assert_called_once()
        calls = [
            call(transaction_uuid=tid,
                 two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                 action=TwoPcAction.PREPARE,
                 data=transaction_data),
            call(transaction_uuid=tid,
                 two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                 action=TwoPcAction.ABORT,
                 data=transaction_data),
        ]
        p1.run_two_pc.assert_has_calls(calls)
        p2.run_two_pc.assert_has_calls(calls)
        mock_local_run_two_pc_action.assert_has_calls([
            call(session=mock.ANY,
                 tid=tid,
                 two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                 action=TwoPcAction.PREPARE,
                 data=transaction_data),
            call(session=mock.ANY,
                 tid=tid,
                 two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                 action=TwoPcAction.ABORT,
                 data=transaction_data),
        ])

    @patch('fedlearner_webconsole.two_pc.transaction_manager.run_two_pc_action')
    def test_do_two_pc_action(self, mock_local_run_two_pc_action):
        tid = 'test-id'
        transaction_data = TransactionData(create_model_job_data=CreateModelJobData(model_job_name='test model name'))
        # Two participants
        p1 = MagicMock()
        p1.run_two_pc = MagicMock(
            return_value=TwoPcResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS), succeeded=True))
        p2 = MagicMock()
        p2.run_two_pc = MagicMock(
            return_value=TwoPcResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS), succeeded=True))
        mock_local_run_two_pc_action.return_value = (True, '')
        # A hack to avoid mocking RpcClient.from_project_and_participant
        tm = TransactionManager(project_name=self._PROJECT_NAME,
                                project_token=self._PROJECT_TOKEN,
                                two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                                participants=[])
        tm._clients = [p1, p2]
        self.assertTrue(tm.do_two_pc_action(tid=tid, action=TwoPcAction.PREPARE, data=transaction_data))
        p1.run_two_pc.assert_called_once_with(transaction_uuid=tid,
                                              two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                                              action=TwoPcAction.PREPARE,
                                              data=transaction_data)
        p2.run_two_pc.assert_called_once_with(transaction_uuid=tid,
                                              two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                                              action=TwoPcAction.PREPARE,
                                              data=transaction_data)
        mock_local_run_two_pc_action.assert_called_once_with(session=mock.ANY,
                                                             tid=tid,
                                                             two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                                                             action=TwoPcAction.PREPARE,
                                                             data=transaction_data)


if __name__ == '__main__':
    unittest.main()

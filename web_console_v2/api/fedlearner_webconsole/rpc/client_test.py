import unittest
import grpc_testing

from unittest.mock import patch
from grpc import StatusCode
from grpc.framework.foundation import logging_pool

from fedlearner_webconsole.proto.service_pb2 import DESCRIPTOR
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.project.models import Project as ProjectModel
from fedlearner_webconsole.proto.common_pb2 import GrpcSpec, Status, StatusCode as FedLearnerStatusCode
from fedlearner_webconsole.proto.project_pb2 import Project, Participant
from fedlearner_webconsole.proto.service_pb2 import CheckConnectionRequest, ProjAuthInfo
from fedlearner_webconsole.testing.utils import create_test_db
from fedlearner_webconsole.proto.service_pb2 import CheckConnectionResponse

TARGET_SERVICE = DESCRIPTOR.services_by_name['WebConsoleV2Service']


class RpcClientTest(unittest.TestCase):
    _TEST_PROJECT_NAME = 'test-project'
    _TEST_RECEIVER_NAME = 'test-receiver'
    _TEST_URL = 'localhost:123'
    _TEST_AUTHORITY = 'test-authority'
    _X_HOST_HEADER_KEY = 'x-host'
    _TEST_X_HOST = 'default.fedlearner.webconsole'

    _DB = create_test_db()

    @classmethod
    def setUpClass(cls):
        grpc_spec = GrpcSpec(
            url=cls._TEST_URL,
            authority=cls._TEST_AUTHORITY,
            extra_headers={
                cls._X_HOST_HEADER_KEY: cls._TEST_X_HOST
            }
        )
        participant = Participant(
            name=cls._TEST_RECEIVER_NAME,
            sender_auth_token='test-sender-auth-token',
            grpc_spec=grpc_spec
        )
        project_config = Project(
            project_name=cls._TEST_PROJECT_NAME,
            self_name=cls._TEST_PROJECT_NAME,
            participants={
                cls._TEST_RECEIVER_NAME: participant
            }
        )

        cls._participant = participant
        cls._project_config = project_config
        cls._project = ProjectModel(name=cls._TEST_PROJECT_NAME)
        cls._project.set_config(project_config)

        # Inserts the project entity
        cls._DB.create_all()
        cls._DB.session.add(cls._project)
        cls._DB.session.commit()

    @classmethod
    def tearDownClass(cls):
        cls._DB.session.remove()
        cls._DB.drop_all()

    def setUp(self):
        self._client_execution_thread_pool = logging_pool.pool(1)

        # Builds a testing channel
        self._fake_channel = grpc_testing.channel(DESCRIPTOR.services_by_name.values(),
                                                  grpc_testing.strict_real_time())
        self._build_channel_patcher = patch('fedlearner_webconsole.rpc.client._build_channel')
        self._mock_build_channel = self._build_channel_patcher.start()
        self._mock_build_channel.return_value = self._fake_channel
        self._client = RpcClient(self._TEST_PROJECT_NAME, self._TEST_RECEIVER_NAME)

        self._mock_build_channel.assert_called_once_with(self._TEST_URL, self._TEST_AUTHORITY)

    def tearDown(self):
        self._build_channel_patcher.stop()
        self._client_execution_thread_pool.shutdown(wait=False)

    def test_check_connection(self):
        call = self._client_execution_thread_pool.submit(
            lambda: self._client.check_connection())

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            TARGET_SERVICE.methods_by_name['CheckConnection']
        )

        self.assertEqual(request, CheckConnectionRequest(
            auth_info=ProjAuthInfo(
                project_name=self._project_config.project_name,
                sender_name=self._project_config.self_name,
                receiver_name=self._participant.name,
                auth_token=self._participant.sender_auth_token)
        ))

        expected_status = Status(
            code=FedLearnerStatusCode.STATUS_SUCCESS,
            msg='test'
        )
        rpc.terminate(
            response=CheckConnectionResponse(
                status=expected_status
            ),
            code=StatusCode.OK,
            trailing_metadata=(),
            details=None
        )
        self.assertEqual(call.result(), expected_status)


if __name__ == '__main__':
    unittest.main()

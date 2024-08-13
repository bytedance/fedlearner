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

import contextlib
import unittest
from unittest.mock import patch

import grpc

from fedlearner_webconsole.db import db
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.testing import service_pb2_grpc
from fedlearner_webconsole.proto.testing.service_pb2 import FakeUnaryUnaryRequest, FakeStreamStreamRequest
from fedlearner_webconsole.rpc.v2.auth_server_interceptor import AuthServerInterceptor, _parse_method_name
from testing.no_web_server_test_case import NoWebServerTestCase
from testing.rpc.client import testing_channel
from testing.rpc.service import TestService


class ParseMethodNameTest(unittest.TestCase):

    def test_parse_method_name(self):
        self.assertEqual(_parse_method_name('/fedlearner_webconsole.proto.testing.TestService/FakeUnaryUnary'),
                         ('fedlearner_webconsole.proto.testing.TestService', 'FakeUnaryUnary'))
        self.assertEqual(_parse_method_name('test-service/TestM'), ('test-service', 'TestM'))


class AuthServerInterceptorTest(NoWebServerTestCase):

    def set_up_client(self, is_project_based=False, skip=False) -> service_pb2_grpc.TestServiceStub:
        if is_project_based:
            project_based_patcher = patch(
                'fedlearner_webconsole.rpc.v2.auth_server_interceptor.PROJECT_BASED_SERVICES',
                frozenset(['fedlearner_webconsole.proto.testing.TestService']),
            )
            project_based_patcher.start()
        if skip:
            skip_patcher = patch(
                'fedlearner_webconsole.rpc.v2.auth_server_interceptor.DISABLED_SERVICES',
                frozenset(['fedlearner_webconsole.proto.testing.TestService']),
            )
            skip_patcher.start()

        def stop_patchers():
            if is_project_based:
                project_based_patcher.stop()
            if skip:
                skip_patcher.stop()

        def register_service(server: grpc.Server):
            service_pb2_grpc.add_TestServiceServicer_to_server(TestService(), server)

        with contextlib.ExitStack() as stack:
            channel = stack.enter_context(
                testing_channel(
                    register_service,
                    server_interceptors=[AuthServerInterceptor()],
                ))
            stub = service_pb2_grpc.TestServiceStub(channel)
            # Cleans up for the server
            self.addCleanup(stack.pop_all().close)
            self.addCleanup(stop_patchers)
            return stub

    def test_verify_domain_name(self):
        stub = self.set_up_client()
        valid_subject_dn = 'CN=aaa.fedlearner.net,OU=security,O=security,L=beijing,ST=beijing,C=CN'
        # Normal unary-unary
        resp = stub.FakeUnaryUnary(request=FakeUnaryUnaryRequest(),
                                   metadata=[('ssl-client-subject-dn', valid_subject_dn)])
        self.assertIsNotNone(resp)

        # Normal stream-stream
        def generate_request():
            yield FakeStreamStreamRequest()

        # Makes sure the stream-stream request is executed
        self.assertEqual(
            len(list(stub.FakeStreamStream(generate_request(),
                                           metadata=[('ssl-client-subject-dn', valid_subject_dn)]))), 1)

        with self.assertRaisesRegex(grpc.RpcError, 'No client subject dn found') as cm:
            # No ssl header
            stub.FakeUnaryUnary(request=FakeUnaryUnaryRequest())
        self.assertEqual(cm.exception.code(), grpc.StatusCode.UNAUTHENTICATED)
        with self.assertRaisesRegex(grpc.RpcError, 'No client subject dn found') as cm:
            # No ssl header
            list(stub.FakeStreamStream(generate_request()))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.UNAUTHENTICATED)
        with self.assertRaisesRegex(grpc.RpcError, 'Invalid subject dn') as cm:
            stub.FakeUnaryUnary(request=FakeUnaryUnaryRequest(),
                                metadata=[('ssl-client-subject-dn', 'invalid subject dn')])
        self.assertEqual(cm.exception.code(), grpc.StatusCode.UNAUTHENTICATED)
        with self.assertRaisesRegex(grpc.RpcError, 'Invalid domain name') as cm:
            stub.FakeUnaryUnary(request=FakeUnaryUnaryRequest(),
                                metadata=[('ssl-client-subject-dn',
                                           'CN=test.net,OU=security,O=security,L=beijing,ST=beijing,C=CN')])
        self.assertEqual(cm.exception.code(), grpc.StatusCode.UNAUTHENTICATED)

    def test_verify_project(self):
        valid_subject_dn = 'CN=test.fedlearner.net,OU=security,O=security,L=beijing,ST=beijing,C=CN'
        with db.session_scope() as session:
            project = Project(id=123, name='test-project')
            participant = Participant(
                id=666,
                name='test-participant',
                domain_name='fl-test.com',
                host='127.0.0.1',
                port=32443,
            )
            relationship = ProjectParticipant(project_id=project.id, participant_id=participant.id)
            session.add_all([project, participant, relationship])
            session.commit()
        stub = self.set_up_client(is_project_based=True)

        # Valid request
        resp = stub.FakeUnaryUnary(request=FakeUnaryUnaryRequest(),
                                   metadata=[('ssl-client-subject-dn', valid_subject_dn),
                                             ('project-name', 'test-project')])
        self.assertIsNotNone(resp)

        # No project name
        with self.assertRaisesRegex(grpc.RpcError, 'No project name found') as cm:
            stub.FakeUnaryUnary(request=FakeUnaryUnaryRequest(), metadata=[('ssl-client-subject-dn', valid_subject_dn)])
        self.assertEqual(cm.exception.code(), grpc.StatusCode.UNAUTHENTICATED)
        # Invalid project
        with self.assertRaisesRegex(grpc.RpcError, 'Invalid project hhh-project') as cm:
            stub.FakeUnaryUnary(request=FakeUnaryUnaryRequest(),
                                metadata=[('ssl-client-subject-dn', valid_subject_dn), ('project-name', 'hhh-project')])
        self.assertEqual(cm.exception.code(), grpc.StatusCode.UNAUTHENTICATED)
        # No access
        with self.assertRaisesRegex(grpc.RpcError, 'No access to test-project') as cm:
            stub.FakeUnaryUnary(request=FakeUnaryUnaryRequest(),
                                metadata=[
                                    ('ssl-client-subject-dn',
                                     'CN=another.fedlearner.net,OU=security,O=security,L=beijing,ST=beijing,C=CN'),
                                    ('project-name', 'test-project')
                                ])
        self.assertEqual(cm.exception.code(), grpc.StatusCode.UNAUTHENTICATED)

    def test_verify_project_unicode(self):
        valid_subject_dn = 'CN=test.fedlearner.net,OU=security,O=security,L=beijing,ST=beijing,C=CN'
        with db.session_scope() as session:
            project = Project(id=123, name='测试工作区')
            participant = Participant(
                id=666,
                name='test-participant',
                domain_name='fl-test.com',
                host='127.0.0.1',
                port=32443,
            )
            relationship = ProjectParticipant(project_id=project.id, participant_id=participant.id)
            session.add_all([project, participant, relationship])
            session.commit()
        stub = self.set_up_client(is_project_based=True)

        # Valid request
        resp = stub.FakeUnaryUnary(request=FakeUnaryUnaryRequest(),
                                   metadata=[('ssl-client-subject-dn', valid_subject_dn),
                                             ('project-name', '5rWL6K+V5bel5L2c5Yy6')])
        self.assertIsNotNone(resp)

    def test_skip(self):
        stub = self.set_up_client(skip=True)
        # No auth related info
        resp = stub.FakeUnaryUnary(request=FakeUnaryUnaryRequest())
        self.assertIsNotNone(resp)


if __name__ == '__main__':
    unittest.main()

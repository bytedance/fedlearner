#  Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  coding: utf-8
from http import HTTPStatus
import unittest
from unittest.mock import MagicMock, patch
from typing import Tuple
from grpc import ServicerContext, StatusCode
from grpc._server import _Context, _RPCState
from google.protobuf import empty_pb2
from google.protobuf.message import Message
from testing.common import BaseTestCase, NoWebServerTestCase

from fedlearner_webconsole.utils.pp_base64 import base64encode
from fedlearner_webconsole.utils.const import API_VERSION
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.audit.decorators import _get_func_params, _infer_rpc_event_fields,\
    emits_rpc_event, get_two_pc_request_uuid
from fedlearner_webconsole.proto.service_pb2 import TwoPcRequest, UpdateWorkflowResponse
from fedlearner_webconsole.proto import common_pb2, service_pb2
from fedlearner_webconsole.audit.models import EventModel
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.two_pc_pb2 import CreateModelJobData, TransactionData, TwoPcAction, TwoPcType
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition, WorkflowDefinition
from fedlearner_webconsole.utils.pp_datetime import now, to_timestamp


def get_uuid(proto_message: Message):
    return 'test_uuid'


def get_times() -> Tuple[int, int]:
    ts = to_timestamp(now())
    return ts - 60 * 2, ts + 60 * 2


@emits_rpc_event(resource_type=Event.ResourceType.WORKFLOW,
                 op_type=Event.OperationType.UPDATE,
                 resource_name_fn=get_uuid)
def fake_rpc_method(request, context=None):
    return UpdateWorkflowResponse(status=common_pb2.Status(code=common_pb2.STATUS_UNAUTHORIZED, msg='done'))


@emits_rpc_event(resource_type=Event.ResourceType.MODEL_JOB_GROUP,
                 op_type=Event.OperationType.UPDATE,
                 resource_name_fn=get_uuid)
def fake_rpc_method_without_status_code(request, context=None):
    return service_pb2.UpdateModelJobGroupResponse(uuid='test',
                                                   config=WorkflowDefinition(job_definitions=[
                                                       JobDefinition(name='train-job',
                                                                     job_type=JobDefinition.JobType.TREE_MODEL_TRAINING,
                                                                     variables=[Variable(name='mode', value='train')])
                                                   ]))


@emits_rpc_event(resource_type=Event.ResourceType.TRUSTED_JOB_GROUP,
                 op_type=Event.OperationType.INFORM,
                 resource_name_fn=get_uuid)
def fake_rpc_method_with_status_code_in_context(request, context: ServicerContext = None):
    context.abort(StatusCode.INVALID_ARGUMENT, 'just test')
    return empty_pb2.Empty()


class DecoratorsTest(BaseTestCase):

    def test_emits_event(self):
        self.signin_as_admin()

        start_time, end_time = get_times()
        response = self.post_helper(
            f'{API_VERSION}/auth/users', {
                'username': 'test123',
                'password': base64encode('123456.@abc'),
                'role': 'USER',
                'name': 'test123',
                'email': 'test@byd.org'
            })
        user_id = self.get_response_data(response).get('id')

        response = self.get_helper(
            f'{API_VERSION}/events?filter=(and(username="admin")(start_time>{start_time})(end_time<{end_time}))')
        data = self.get_response_data(response)[0]
        self.assertEqual(Event.OperationType.CREATE, Event.OperationType.Value(data.get('op_type')))
        self.assertEqual(Event.ResourceType.USER, Event.ResourceType.Value(data.get('resource_type')))
        self.assertEqual('4', data.get('resource_name').split('/')[-1])

        # send a wrong request and see if the event is logged correctly
        response = self.patch_helper(f'{API_VERSION}/auth/users/999', {})
        self.assertStatus(response, HTTPStatus.NOT_FOUND)
        response = self.get_helper(
            f'{API_VERSION}/events?filter=(and(username="admin")(start_time>{start_time})(end_time<{end_time}))')
        self.assertEqual(Event.OperationType.UPDATE,
                         Event.OperationType.Value(self.get_response_data(response)[0].get('op_type')))
        self.assertEqual(Event.Result.FAILURE, Event.Result.Value(self.get_response_data(response)[0].get('result')))

        self.patch_helper(f'{API_VERSION}/auth/users/{user_id}', {})
        response = self.get_helper(
            f'{API_VERSION}/events?filter=(and(username="admin")(start_time>{start_time})(end_time<{end_time}))')
        self.assertEqual(Event.Result.SUCCESS, Event.Result.Value(self.get_response_data(response)[0].get('result')))

        self.delete_helper(f'{API_VERSION}/auth/users/{user_id}')
        response = self.get_helper(
            f'{API_VERSION}/events?filter=(and(username="admin")(start_time>{start_time})(end_time<{end_time}))')
        self.assertEqual(Event.OperationType.DELETE,
                         Event.OperationType.Value(self.get_response_data(response)[0].get('op_type')))


class RpcDecoratorsTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        self.default_auth_info = service_pb2.ProjAuthInfo(project_name='test', target_domain='test_domain')
        self.request = service_pb2.UpdateWorkflowRequest(auth_info=self.default_auth_info)
        self.context = _Context('11', _RPCState(), '22')

    @patch('fedlearner_webconsole.audit.decorators._infer_auth_info')
    def test_decorator(self, mock_infer_auth_info: MagicMock):
        mock_infer_auth_info.return_value = 'bytedance', 1
        fake_rpc_method(self.request, context=self.context)
        with db.session_scope() as session:
            workflow_event = session.query(EventModel).first()
            self.assertEqual(workflow_event.op_type, Event.OperationType.Name(Event.OperationType.UPDATE))
            self.assertEqual(workflow_event.resource_type, Event.ResourceType.Name(Event.ResourceType.WORKFLOW))
            self.assertEqual(workflow_event.resource_name, 'test_uuid')
            self.assertEqual(workflow_event.coordinator_pure_domain_name, 'bytedance')
            self.assertEqual(workflow_event.project_id, 1)
            self.assertEqual(workflow_event.result_code, 'UNAUTHENTICATED')
            self.assertEqual(workflow_event.result, 'FAILURE')
            self.assertEqual(workflow_event.name, 'UpdateWorkflow')

    def test_get_func_params(self):
        func_params = _get_func_params(fake_rpc_method, request=self.request, context=self.context)
        self.assertEqual(len(func_params), 2)
        self.assertEqual(func_params['request'], self.request)
        self.assertEqual(func_params['context'], self.context)

    def test_infer_rpc_event_fields_with_two_pc(self):
        transaction_data = TransactionData(
            create_model_job_data=CreateModelJobData(model_job_name='test model name', model_job_uuid='test uuid'))
        request = TwoPcRequest(auth_info=self.default_auth_info,
                               transaction_uuid='test-id',
                               type=TwoPcType.CREATE_MODEL_JOB,
                               action=TwoPcAction.PREPARE,
                               data=transaction_data)
        func_params = _get_func_params(fake_rpc_method, request=request, context=self.context)
        fields = _infer_rpc_event_fields(func_params, Event.ResourceType.UNKNOWN_RESOURCE_TYPE, get_uuid,
                                         Event.OperationType.UNKNOWN_OPERATION_TYPE)
        uuid = get_two_pc_request_uuid(request)
        self.assertEqual(uuid, request.data.create_model_job_data.model_job_uuid)
        self.assertEqual(fields['op_type'], Event.OperationType.CREATE)
        self.assertEqual(fields['resource_type'], Event.ResourceType.MODEL_JOB)
        self.assertEqual(fields['name'], 'TwoPc')

        request = TwoPcRequest(auth_info=self.default_auth_info,
                               transaction_uuid='test-id',
                               type=TwoPcType.CONTROL_WORKFLOW_STATE,
                               action=TwoPcAction.PREPARE)
        func_params = _get_func_params(fake_rpc_method, request=request, context=self.context)
        fields = _infer_rpc_event_fields(func_params, Event.ResourceType.UNKNOWN_RESOURCE_TYPE, get_uuid,
                                         Event.OperationType.UNKNOWN_OPERATION_TYPE)
        self.assertEqual(fields['op_type'], Event.OperationType.CONTROL_STATE)
        self.assertEqual(fields['resource_type'], Event.ResourceType.WORKFLOW)

        request = TwoPcRequest(auth_info=self.default_auth_info,
                               transaction_uuid='test-id',
                               type=TwoPcType.CREATE_MODEL_JOB_GROUP,
                               action=TwoPcAction.PREPARE)
        func_params = _get_func_params(fake_rpc_method, request=request, context=self.context)
        fields = _infer_rpc_event_fields(func_params, Event.ResourceType.UNKNOWN_RESOURCE_TYPE, get_uuid,
                                         Event.OperationType.UNKNOWN_OPERATION_TYPE)
        self.assertEqual(fields['op_type'], Event.OperationType.CREATE)
        self.assertEqual(fields['resource_type'], Event.ResourceType.MODEL_JOB_GROUP)

        request = TwoPcRequest(auth_info=self.default_auth_info,
                               transaction_uuid='test-id',
                               type=TwoPcType.LAUNCH_DATASET_JOB,
                               action=TwoPcAction.PREPARE)
        func_params = _get_func_params(fake_rpc_method, request=request, context=self.context)
        fields = _infer_rpc_event_fields(func_params, Event.ResourceType.UNKNOWN_RESOURCE_TYPE, get_uuid,
                                         Event.OperationType.UNKNOWN_OPERATION_TYPE)
        self.assertEqual(fields['op_type'], Event.OperationType.LAUNCH)
        self.assertEqual(fields['resource_type'], Event.ResourceType.DATASET_JOB)

        request = TwoPcRequest(auth_info=self.default_auth_info,
                               transaction_uuid='test-id',
                               type=TwoPcType.LAUNCH_MODEL_JOB,
                               action=TwoPcAction.PREPARE)
        func_params = _get_func_params(fake_rpc_method, request=request, context=self.context)
        fields = _infer_rpc_event_fields(func_params, Event.ResourceType.UNKNOWN_RESOURCE_TYPE, get_uuid,
                                         Event.OperationType.UNKNOWN_OPERATION_TYPE)
        self.assertEqual(fields['op_type'], Event.OperationType.LAUNCH)
        self.assertEqual(fields['resource_type'], Event.ResourceType.MODEL_JOB)

        request = TwoPcRequest(auth_info=self.default_auth_info,
                               transaction_uuid='test-id',
                               type=TwoPcType.STOP_DATASET_JOB,
                               action=TwoPcAction.PREPARE)
        func_params = _get_func_params(fake_rpc_method, request=request, context=self.context)
        fields = _infer_rpc_event_fields(func_params, Event.ResourceType.UNKNOWN_RESOURCE_TYPE, get_uuid,
                                         Event.OperationType.UNKNOWN_OPERATION_TYPE)
        self.assertEqual(fields['op_type'], Event.OperationType.STOP)
        self.assertEqual(fields['resource_type'], Event.ResourceType.DATASET_JOB)

    @patch('fedlearner_webconsole.audit.decorators._infer_auth_info')
    def test_response_with_no_status(self, mock_infer_auth_info: MagicMock):
        mock_infer_auth_info.return_value = 'bytedance', 1
        fake_rpc_method_without_status_code(self.request, context=self.context)
        with db.session_scope() as session:
            event = session.query(EventModel).first()
            self.assertEqual(event.result_code, 'OK')
            self.assertEqual(event.result, 'SUCCESS')

    @patch('fedlearner_webconsole.audit.decorators._infer_auth_info')
    def test_response_with_status_code_in_context(self, mock_infer_auth_info: MagicMock):
        mock_infer_auth_info.return_value = 'bytedance', 1
        with self.assertRaises(Exception):
            fake_rpc_method_with_status_code_in_context(self.request, context=self.context)
        with db.session_scope() as session:
            event = session.query(EventModel).first()
            self.assertEqual(event.result_code, 'INVALID_ARGUMENT')
            self.assertEqual(event.result, 'FAILURE')


if __name__ == '__main__':
    unittest.main()

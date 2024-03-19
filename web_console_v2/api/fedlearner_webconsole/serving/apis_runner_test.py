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

import json
import unittest
from http import HTTPStatus
from multiprocessing import Queue
from unittest.mock import MagicMock, patch

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.db import db
from fedlearner_webconsole.mmgr.models import Model, ModelJobGroup
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto import service_pb2, serving_pb2, common_pb2
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, ModelSignatureParserInput
from fedlearner_webconsole.serving.models import ServingModel, ServingNegotiator, ServingModelStatus
from fedlearner_webconsole.serving.runners import ModelSignatureParser, QueryParticipantStatusRunner, UpdateModelRunner
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from testing.common import BaseTestCase


def _get_create_serving_service_input(name, model_id: int):
    res = {
        'name': name,
        'comment': 'test-comment-1',
        'model_id': model_id,
        'is_local': True,
        'resource': {
            'cpu': '2',
            'memory': '2',
            'replicas': 3,
        }
    }
    return res


def _fake_update_parsed_signature_sub_process(q: Queue, model_path: str):
    mock_signature_type_dict = {
        '4s_code_ctr': 'DT_FLOAT',
        'event_name_ctr': 'DT_FLOAT',
        'source_account_ctr': 'DT_FLOAT',
        'source_channel_ctr': 'DT_FLOAT',
        'example_id': 'DT_STRING',
        'raw_id': 'DT_INT64',
    }
    mock_parsed_example = serving_pb2.ServingServiceSignature()
    for key, value in mock_signature_type_dict.items():
        mock_example_input = serving_pb2.ServingServiceSignatureInput(name=key, type=value)
        mock_parsed_example.inputs.append(mock_example_input)
    q.put(mock_parsed_example)


class ServingServicesApiRunnerTest(BaseTestCase):

    def setUp(self):
        self.maxDiff = None
        super().setUp()
        # insert project
        with db.session_scope() as session:
            project = Project()
            project.name = 'test_project_name'
            session.add(project)
            session.flush([project])

            participant = Participant()
            participant.name = 'test_participant_name'
            participant.domain_name = 'test_domain_name'
            participant.project_id = project.id
            session.add(participant)
            session.flush([participant])

            project_participant = ProjectParticipant()
            project_participant.participant_id = participant.id
            project_participant.project_id = project.id
            session.add(project_participant)

            model_job_group = ModelJobGroup()
            session.add(model_job_group)
            session.flush([model_job_group])

            model = Model()
            model.name = 'test_model_name'
            model.model_path = '/test_path/'
            model.group_id = model_job_group.id
            model.uuid = 'test_uuid_1'
            model.project_id = project.id
            model.version = 1

            session.add(model)
            session.commit()
            self.project_id = project.id
            self.model_id = model.id
            self.model_uuid = model.uuid
            self.model_group_id = model_job_group.id

    @patch('fedlearner_webconsole.rpc.client.RpcClient.operate_serving_service')
    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_query_participant_runner(self, mock_create_deployment: MagicMock, mock_federal_operation: MagicMock):
        mock_federal_operation.return_value = service_pb2.ServingServiceResponse(
            status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS), code=serving_pb2.SERVING_SERVICE_SUCCESS)
        # create federal serving service
        name = 'test-serving-service-1'
        serving_service = _get_create_serving_service_input(name, model_id=self.model_id)
        serving_service['is_local'] = False
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        # create another federal serving service
        name = 'test-serving-service-2'
        serving_service = _get_create_serving_service_input(name, model_id=self.model_id)
        serving_service['is_local'] = False
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        # create another local serving service
        name = 'test-serving-service-3'
        serving_service = _get_create_serving_service_input(name, model_id=self.model_id)
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        # check status
        with db.session_scope() as session:
            query = session.query(ServingNegotiator)
            query = query.filter(ServingNegotiator.is_local.is_(False))
            query = query.outerjoin(
                ServingNegotiator.serving_model).filter(ServingModel.status == ServingModelStatus.PENDING_ACCEPT)
            all_records = query.all()
            self.assertEqual(len(all_records), 2)

        # call query runner
        runner = QueryParticipantStatusRunner()
        test_context = RunnerContext(0, RunnerInput())
        runner_status, _ = runner.run(test_context)
        self.assertEqual(runner_status, RunnerStatus.DONE)

        # check status again
        with db.session_scope() as session:
            query = session.query(ServingNegotiator)
            query = query.filter(ServingNegotiator.is_local.is_(False))
            query = query.outerjoin(
                ServingNegotiator.serving_model).filter(ServingModel.status == ServingModelStatus.PENDING_ACCEPT)
            all_records = query.all()
            self.assertEqual(len(all_records), 0)

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_query_participant_runner_exception_branch(self, mock_create_deployment: MagicMock):
        serving_model = ServingModel()
        serving_model.project_id = self.project_id
        serving_model.name = 'test_serving_model_name'
        serving_model.status = ServingModelStatus.PENDING_ACCEPT
        serving_negotiator = ServingNegotiator()
        serving_negotiator.project_id = self.project_id
        serving_negotiator.is_local = False
        with db.session_scope() as session:
            session.add(serving_model)
            session.flush([serving_model])
            serving_negotiator.serving_model_id = serving_model.id
            session.add(serving_negotiator)
            session.commit()

        # call query runner
        runner = QueryParticipantStatusRunner()
        test_context = RunnerContext(0, RunnerInput())
        runner_status, _ = runner.run(test_context)
        self.assertEqual(runner_status, RunnerStatus.DONE)

    @patch('fedlearner_webconsole.rpc.client.RpcClient.operate_serving_service')
    @patch('fedlearner_webconsole.serving.services.TensorflowServingService.get_model_signature')
    @patch('fedlearner_webconsole.serving.runners._update_parsed_signature', _fake_update_parsed_signature_sub_process)
    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_parse_signature_runner(self, mock_create_deployment: MagicMock, get_model_signature: MagicMock,
                                    mock_federal_operation: MagicMock):
        mock_federal_operation.return_value = service_pb2.ServingServiceResponse(
            status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS), code=serving_pb2.SERVING_SERVICE_SUCCESS)
        get_model_signature.return_value = {
            'inputs': {
                'act1_f': {
                    'name': 'act1_f:0',
                    'dtype': 'DT_FLOAT',
                    'tensorShape': {
                        'unknownRank': True
                    }
                },
                'examples': {
                    'name': 'examples:0',
                    'dtype': 'DT_STRING',
                    'tensorShape': {
                        'unknownRank': True
                    }
                }
            },
            'outputs': {
                'output': {
                    'name': 'Sigmoid:0',
                    'dtype': 'DT_FLOAT',
                    'tensorShape': {
                        'unknownRank': True
                    }
                }
            },
            'methodName': 'tensorflow/serving/predict'
        }
        # create serving service
        name = 'test-serving-service-1'
        serving_service = _get_create_serving_service_input(name, model_id=self.model_id)
        serving_service['is_local'] = False
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        data = self.get_response_data(response)
        serving_model_id = data['id']  # get id from create response

        # call signature runner
        runner = ModelSignatureParser()
        runner_input = RunnerInput(model_signature_parser_input=ModelSignatureParserInput(
            serving_model_id=serving_model_id))
        runner.run(RunnerContext(0, runner_input))

        # check db
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).get(serving_model_id)
            self.assertEqual(serving_model.name, name)
            self.assertEqual(serving_model.status, ServingModelStatus.PENDING_ACCEPT)
            signature_dict = json.loads(serving_model.signature)
            self.assertEqual(len(signature_dict['inputs']), 6)
            self.assertIn('from_participants', signature_dict)
            self.assertIn('act1_f', signature_dict['from_participants'])
            self.assertIn('outputs', signature_dict)
            self.assertIn('output', signature_dict['outputs'])
            serving_negotiator = session.query(ServingNegotiator).filter_by(
                serving_model_id=serving_model_id).one_or_none()
            self.assertIsNotNone(serving_negotiator)
            self.assertEqual(serving_negotiator.project_id, self.project_id)
            self.assertEqual(serving_negotiator.with_label, True)
            raw_signature_dict = json.loads(serving_negotiator.raw_signature)
            self.assertIn('inputs', raw_signature_dict)
            self.assertIn('outputs', raw_signature_dict)

    @patch('fedlearner_webconsole.rpc.client.RpcClient.operate_serving_service')
    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_update_model_runner(self, mock_create_deployment: MagicMock, mock_federal_operation: MagicMock):
        mock_federal_operation.return_value = service_pb2.ServingServiceResponse(
            status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS), code=serving_pb2.SERVING_SERVICE_SUCCESS)
        # create federal serving service
        name = 'test-auto-update-1'
        serving_service = {
            'name': name,
            'comment': 'test-comment-1',
            'model_group_id': self.model_group_id,
            'is_local': True,
            'resource': {
                'cpu': '2',
                'memory': '2',
                'replicas': 3,
            }
        }
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        data = self.get_response_data(response)
        serving_model_id = data['id']  # get id from create response

        # create anothor model
        with db.session_scope() as session:
            model = Model()
            model.name = 'test_model_name_2'
            model.model_path = '/test_path_2/'
            model.group_id = self.model_group_id
            model.uuid = 'test_uuid_2'
            model.project_id = self.project_id
            model.version = 2
            session.add(model)
            session.commit()
            model_id_2 = model.id

        # check status
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).filter_by(id=serving_model_id).one_or_none()
            self.assertEqual(serving_model.model_group_id, self.model_group_id)
            self.assertEqual(serving_model.model_id, self.model_id)

        # call update model runner
        runner = UpdateModelRunner()
        test_context = RunnerContext(0, RunnerInput())
        runner_status, _ = runner.run(test_context)
        self.assertEqual(runner_status, RunnerStatus.DONE)

        # check status again
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).filter_by(id=serving_model_id).one_or_none()
            self.assertEqual(serving_model.model_group_id, self.model_group_id)
            self.assertEqual(serving_model.model_id, model_id_2)


if __name__ == '__main__':
    unittest.main()

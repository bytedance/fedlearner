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
from unittest.mock import MagicMock, patch

import numpy as np

from tensorflow.core.example.example_pb2 import Example
from tensorflow.core.example.feature_pb2 import Feature, Int64List, Features

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.db import db
from fedlearner_webconsole.mmgr.models import Model
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto import service_pb2, serving_pb2, common_pb2
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput
from fedlearner_webconsole.serving.database_fetcher import DatabaseFetcher
from fedlearner_webconsole.serving.models import ServingModel, ServingModelStatus
from fedlearner_webconsole.serving.runners import QueryParticipantStatusRunner
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.serving.services import NegotiatorServingService
from testing.common import BaseTestCase

TEST_SIGNATURE = {
    'inputs': [{
        'name': 'example_id',
        'type': 'DT_STRING'
    }, {
        'name': 'raw_id',
        'type': 'DT_STRING'
    }, {
        'name': 'x0',
        'type': 'DT_FLOAT'
    }, {
        'name': 'x1',
        'type': 'DT_INT64',
        'dim': [4]
    }],
    'from_participants': {
        'act1_f': {
            'name': 'act1_f:0',
            'dtype': 'DT_FLOAT',
            'tensorShape': {
                'unknownRank': True
            }
        },
        'act2_f': {
            'name': 'act2_f:0',
            'dtype': 'DT_DOUBLE'
        },
        'act3_f': {
            'name': 'act3_f:0',
            'dtype': 'DT_INT32'
        },
        'act4_f': {
            'name': 'act4_f:0',
            'dtype': 'DT_INT64'
        },
        'act5_f': {
            'name': 'act5_f:0',
            'dtype': 'DT_UINT32'
        },
        'act6_f': {
            'name': 'act6_f:0',
            'dtype': 'DT_UINT64'
        },
        'act7_f': {
            'name': 'act7_f:0',
            'dtype': 'DT_STRING'
        },
        'act8_f': {
            'name': 'act8_f:0',
            'dtype': 'DT_BOOL'
        }
    }
}

TEST_OUTPUT = {
    'result': {
        'act1_f': {
            'dtype': 'DT_FLOAT',
            'floatVal': 0.1
        },
        'act2_f': {
            'dtype': 'DT_DOUBLE',
            'doubleVal': 0.1
        },
        'act3_f': {
            'dtype': 'DT_INT32',
            'intVal': -11
        },
        'act4_f': {
            'dtype': 'DT_INT64',
            'int64Val': -12
        },
        'act5_f': {
            'dtype': 'DT_UINT32',
            'uint32Val': 13
        },
        'act6_f': {
            'dtype': 'DT_UINT64',
            'uint64Val': 14
        },
        'act7_f': {
            'dtype': 'DT_STRING',
            'stringVal': 'test'
        },
        'act8_f': {
            'dtype': 'DT_BOOL',
            'boolVal': False
        },
    }
}


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


class ServingServicesApiInferenceTest(BaseTestCase):

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

            model = Model()
            model.name = 'test_model_name'
            model.model_path = '/test_path/'
            model.group_id = 1
            model.uuid = 'test_uuid_1'
            model.project_id = project.id

            session.add(model)
            session.commit()
            self.project_id = project.id
            self.model_id = model.id
            self.model_uuid = model.uuid

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_post_serving_service_inference(self, mock_create_deployment: MagicMock):
        # create
        name = 'test-serving-service-1'
        serving_service = _get_create_serving_service_input(name, model_id=self.model_id)
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        data = self.get_response_data(response)
        serving_model_id = data['id']  # get id from create response
        # make input
        fake_data = {
            'raw': Feature(int64_list=Int64List(value=np.random.randint(low=0, high=255, size=(128 * 128 * 3)))),
            'label': Feature(int64_list=Int64List(value=[1]))
        }
        fake_input = {
            'input_data': str(Example(features=Features(feature=fake_data))),
        }
        # post
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services/{serving_model_id}/inference',
                                    data=fake_input)
        self.assertEqual(HTTPStatus.INTERNAL_SERVER_ERROR, response.status_code)
        data = self.get_response_data(response)
        self.assertIsNone(data)

    @patch('fedlearner_webconsole.rpc.client.RpcClient.operate_serving_service')
    @patch('fedlearner_webconsole.rpc.client.RpcClient.inference_serving_service')
    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_post_federal_serving_service_inference(self, mock_create_deployment: MagicMock,
                                                    mock_federal_inference: MagicMock,
                                                    mock_federal_operation: MagicMock):
        mock_inference_response = service_pb2.ServingServiceInferenceResponse(
            status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS), code=serving_pb2.SERVING_SERVICE_SUCCESS)
        mock_inference_response.data.update(TEST_OUTPUT)
        mock_federal_inference.return_value = mock_inference_response
        mock_federal_operation.return_value = service_pb2.ServingServiceResponse(
            status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS), code=serving_pb2.SERVING_SERVICE_SUCCESS)
        # create serving service
        name = 'test-serving-service-1'
        serving_service = _get_create_serving_service_input(name, model_id=self.model_id)
        serving_service['is_local'] = False
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        data = self.get_response_data(response)
        serving_model_id = data['id']  # get id from create response

        # mock signature runner
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).get(serving_model_id)
            serving_model.signature = json.dumps(TEST_SIGNATURE)
            session.commit()

        # mock query runner
        runner = QueryParticipantStatusRunner()
        test_context = RunnerContext(0, RunnerInput())
        runner_status, _ = runner.run(test_context)
        self.assertEqual(runner_status, RunnerStatus.DONE)
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).get(serving_model_id)
            self.assertEqual(serving_model.status, ServingModelStatus.LOADING)

        # inference, make input
        fake_data = {
            'raw': Feature(int64_list=Int64List(value=np.random.randint(low=0, high=255, size=(128 * 128 * 3)))),
            'label': Feature(int64_list=Int64List(value=[1]))
        }
        fake_input = {
            'input_data': str(Example(features=Features(feature=fake_data))),
        }
        # post
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services/{serving_model_id}/inference',
                                    data=fake_input)
        self.assertEqual(HTTPStatus.INTERNAL_SERVER_ERROR, response.status_code)
        data = self.get_response_data(response)
        self.assertIsNone(data)

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_federal_serving_service_inference_from_participant(self, mock_create_deployment: MagicMock):
        mock_serving_uuid = 'test_uuid_1'
        mock_serving_model_name = 'test_serving_model_name_1'
        # create from participant
        with db.session_scope() as session:
            project = session.query(Project).get(self.project_id)
            request = service_pb2.ServingServiceRequest()
            request.operation_type = serving_pb2.ServingServiceType.SERVING_SERVICE_CREATE
            request.serving_model_uuid = mock_serving_uuid
            request.model_uuid = self.model_uuid
            request.serving_model_name = mock_serving_model_name
            NegotiatorServingService(session).handle_participant_request(request, project)

        # get list
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services')
        data = self.get_response_data(response)
        serving_model_id = data[0]['id']

        # get one
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services/{serving_model_id}')
        data = self.get_response_data(response)
        self.assertEqual('WAITING_CONFIG', data['status'])

        # config
        serving_service = {
            'comment': 'test-comment-1',
            'model_id': self.model_id,
            'resource': {
                'cpu': '2',
                'memory': '2',
                'replicas': 3,
            }
        }
        response = self.patch_helper(f'/api/v2/projects/{self.project_id}/serving_services/{serving_model_id}',
                                     data=serving_service)
        data = self.get_response_data(response)

        # get one
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services/{serving_model_id}')
        data = self.get_response_data(response)
        self.assertEqual('LOADING', data['status'])

        # inference from participant
        query_key = 1
        test_signature = json.dumps(TEST_SIGNATURE)
        data_record = DatabaseFetcher.fetch_by_int_key(query_key, test_signature)
        self.assertEqual(len(data_record['x0']), 1)
        self.assertEqual(data_record['x0'][0], 0.1)
        self.assertEqual(len(data_record['x1']), 4)
        self.assertEqual(data_record['x1'][0], 1)


if __name__ == '__main__':
    unittest.main()

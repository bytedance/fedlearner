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

import grpc
import unittest
import grpc_testing
from google.protobuf.descriptor import ServiceDescriptor
from google.protobuf.empty_pb2 import Empty

from testing.rpc.client import RpcClientTestCase
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.dataset.models import DatasetKindV2, ResourceState
from fedlearner_webconsole.proto.rpc.v2 import resource_service_pb2
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmPb, AlgorithmProjectPb
from fedlearner_webconsole.proto.dataset_pb2 import ParticipantDatasetRef, TimeRange
from fedlearner_webconsole.proto.rpc.v2.resource_service_pb2 import GetAlgorithmRequest, GetAlgorithmProjectRequest, \
    InformDatasetRequest, ListAlgorithmProjectsRequest, ListAlgorithmProjectsResponse, ListAlgorithmsRequest, \
    ListAlgorithmsResponse, GetAlgorithmFilesRequest, GetAlgorithmFilesResponse, ListDatasetsRequest, \
    ListDatasetsResponse
from fedlearner_webconsole.rpc.v2.resource_service_client import ResourceServiceClient

_SERVER_DESCRIPTOR: ServiceDescriptor = resource_service_pb2.DESCRIPTOR.services_by_name['ResourceService']


class ResourceServiceClientTest(RpcClientTestCase):

    def setUp(self):
        super().setUp()
        self._fake_channel: grpc_testing.Channel = grpc_testing.channel([_SERVER_DESCRIPTOR],
                                                                        grpc_testing.strict_real_time())
        self._client = ResourceServiceClient(self._fake_channel)

    def test_list_algorithm_projects(self):
        call = self.client_execution_pool.submit(self._client.list_algorithm_projects)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['ListAlgorithmProjects'])
        algorithm_projects = [
            AlgorithmProjectPb(uuid='1', name='algo-project-1', type='NN_LOCAL', source='USER'),
            AlgorithmProjectPb(uuid='2', name='algo-project-2', type='NN_VERTICAL', source='USER')
        ]
        expected_response = ListAlgorithmProjectsResponse(algorithm_projects=algorithm_projects)
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, ListAlgorithmProjectsRequest())
        self.assertEqual(call.result(), expected_response)

    def test_list_algorithms(self):
        call = self.client_execution_pool.submit(self._client.list_algorithms, algorithm_project_uuid='1')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['ListAlgorithms'])
        algorithms = [
            AlgorithmPb(uuid='1', name='test-algo-1', version=1, type='NN_LOCAL', source='USER'),
            AlgorithmPb(uuid='2', name='test-algo-2', version=2, type='NN_VERTICAL', source='USER')
        ]
        expected_response = ListAlgorithmsResponse(algorithms=algorithms)
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, ListAlgorithmsRequest(algorithm_project_uuid='1'))
        self.assertEqual(call.result(), expected_response)

    def test_get_algorithm_project(self):
        call = self.client_execution_pool.submit(self._client.get_algorithm_project, algorithm_project_uuid='1')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['GetAlgorithmProject'])
        expected_response = AlgorithmProjectPb(uuid='1', name='test-algo-project')
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, GetAlgorithmProjectRequest(algorithm_project_uuid='1'))
        self.assertEqual(call.result(), expected_response)

    def test_get_algorithm(self):
        call = self.client_execution_pool.submit(self._client.get_algorithm, algorithm_uuid='1')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['GetAlgorithm'])
        expected_response = AlgorithmPb(uuid='1', name='test-algo')
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, GetAlgorithmRequest(algorithm_uuid='1'))
        self.assertEqual(call.result(), expected_response)

    def test_get_algorithm_files(self):
        call = self.client_execution_pool.submit(self._client.get_algorithm_files, algorithm_uuid='1')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_stream(
            _SERVER_DESCRIPTOR.methods_by_name['GetAlgorithmFiles'])
        resp = GetAlgorithmFilesResponse(hash='ac3ee699961c58ef80a78c2434efe0d0', chunk=b'')
        rpc.send_response(resp)
        rpc.send_response(resp)
        rpc.terminate(
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, GetAlgorithmFilesRequest(algorithm_uuid='1'))
        resps = list(call.result())
        self.assertEqual(len(resps), 2)
        for res in resps:
            self.assertEqual(res, resp)

    def test_inform_dataset(self):
        call = self.client_execution_pool.submit(self._client.inform_dataset,
                                                 dataset_uuid='test dataset uuid',
                                                 auth_status=AuthStatus.AUTHORIZED)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['InformDataset'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, InformDatasetRequest(uuid='test dataset uuid',
                                                       auth_status=AuthStatus.AUTHORIZED.name))
        self.assertEqual(call.result(), expected_response)

    def test_list_datasets(self):
        # test no args
        call = self.client_execution_pool.submit(self._client.list_datasets)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['ListDatasets'])
        participant_datasets_ref = [
            ParticipantDatasetRef(uuid='dataset_1 uuid', project_id=1, name='dataset_1'),
            ParticipantDatasetRef(uuid='dataset_2 uuid', project_id=1, name='dataset_2')
        ]
        expected_response = ListDatasetsResponse(participant_datasets=participant_datasets_ref)
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, ListDatasetsRequest())
        self.assertEqual(call.result(), expected_response)
        # test has args
        call = self.client_execution_pool.submit(self._client.list_datasets,
                                                 kind=DatasetKindV2.RAW,
                                                 uuid='dataset_1 uuid',
                                                 state=ResourceState.SUCCEEDED,
                                                 time_range=TimeRange(days=1))
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['ListDatasets'])
        participant_datasets_ref = [ParticipantDatasetRef(uuid='dataset_1 uuid', project_id=1, name='dataset_1')]
        expected_response = ListDatasetsResponse(participant_datasets=participant_datasets_ref)
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(
            request,
            ListDatasetsRequest(kind='RAW', uuid='dataset_1 uuid', state='SUCCEEDED', time_range=TimeRange(days=1)))
        self.assertEqual(call.result(), expected_response)


if __name__ == '__main__':
    unittest.main()

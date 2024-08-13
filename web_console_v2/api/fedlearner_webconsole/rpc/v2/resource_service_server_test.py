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
from unittest.mock import ANY, patch, MagicMock
from concurrent import futures
from datetime import datetime, timedelta
from google.protobuf.json_format import ParseDict

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.rpc.v2.resource_service_server import ResourceServiceServicer
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.algorithm.models import AlgorithmProject, Algorithm, AlgorithmType, Source, PublishStatus,\
    AlgorithmParameter
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobKind, DatasetJobState, DatasetKindV2,\
    DatasetType, ResourceState
from fedlearner_webconsole.utils.filtering import parse_expression
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.flask_utils import to_dict
from fedlearner_webconsole.proto.rpc.v2 import resource_service_pb2_grpc
from fedlearner_webconsole.proto.dataset_pb2 import TimeRange
from fedlearner_webconsole.proto.rpc.v2.resource_service_pb2 import InformDatasetRequest, \
    ListAlgorithmProjectsRequest, ListAlgorithmsRequest, GetAlgorithmRequest, GetAlgorithmFilesRequest, \
    GetAlgorithmProjectRequest, ListDatasetsRequest
from fedlearner_webconsole.proto.project_pb2 import ParticipantInfo, ParticipantsInfo


class ResourceServiceTest(NoWebServerTestCase):
    LISTEN_PORT = 1989

    def setUp(self):
        super().setUp()
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
        resource_service_pb2_grpc.add_ResourceServiceServicer_to_server(ResourceServiceServicer(), self._server)
        self._server.add_insecure_port(f'[::]:{self.LISTEN_PORT}')
        self._server.start()
        self._channel = grpc.insecure_channel(target=f'localhost:{self.LISTEN_PORT}')
        self._stub = resource_service_pb2_grpc.ResourceServiceStub(self._channel)

        with db.session_scope() as session:
            project1 = Project(id=1, name='project-1')
            project2 = Project(id=2, name='project-2')
            algo_project1 = AlgorithmProject(id=1,
                                             project_id=1,
                                             uuid='algo-project-uuid-1',
                                             name='algo-project-1',
                                             type=AlgorithmType.NN_LOCAL,
                                             source=Source.USER,
                                             latest_version=1,
                                             publish_status=PublishStatus.PUBLISHED,
                                             comment='comment-1',
                                             created_at=datetime(2012, 1, 14, 12, 0, 5),
                                             updated_at=datetime(2012, 1, 14, 12, 0, 5))
            algo_project2 = AlgorithmProject(id=2,
                                             project_id=1,
                                             uuid='algo-project-uuid-2',
                                             name='algo-project-2',
                                             type=AlgorithmType.NN_VERTICAL,
                                             source=Source.THIRD_PARTY,
                                             latest_version=2,
                                             publish_status=PublishStatus.PUBLISHED,
                                             comment='comment-2',
                                             created_at=datetime(2012, 1, 14, 12, 0, 5),
                                             updated_at=datetime(2012, 1, 14, 12, 0, 5))
            algo_project3 = AlgorithmProject(id=3,
                                             project_id=1,
                                             uuid='algo-project-uuid-3',
                                             name='algo-project-3',
                                             type=AlgorithmType.NN_VERTICAL,
                                             source=Source.USER,
                                             latest_version=3,
                                             publish_status=PublishStatus.UNPUBLISHED,
                                             comment='comment-3',
                                             created_at=datetime(2012, 1, 14, 12, 0, 5),
                                             updated_at=datetime(2012, 1, 14, 12, 0, 5))
            algo_project4 = AlgorithmProject(id=4,
                                             project_id=2,
                                             uuid='algo-project-uuid-4',
                                             name='algo-project-4',
                                             type=AlgorithmType.NN_VERTICAL,
                                             source=Source.USER,
                                             latest_version=4,
                                             publish_status=PublishStatus.UNPUBLISHED,
                                             comment='comment-4',
                                             created_at=datetime(2012, 1, 14, 12, 0, 5),
                                             updated_at=datetime(2012, 1, 14, 12, 0, 5))
            algo1 = Algorithm(id=1,
                              algorithm_project_id=1,
                              project_id=1,
                              name='algo-1',
                              uuid='algo-uuid-1',
                              version=1,
                              publish_status=PublishStatus.PUBLISHED,
                              type=AlgorithmType.NN_VERTICAL,
                              source=Source.USER,
                              comment='comment-1',
                              created_at=datetime(2012, 1, 14, 12, 0, 5),
                              updated_at=datetime(2012, 1, 15, 12, 0, 5))
            algo2 = Algorithm(id=2,
                              algorithm_project_id=1,
                              project_id=1,
                              name='algo-2',
                              uuid='algo-uuid-2',
                              version=2,
                              publish_status=PublishStatus.PUBLISHED,
                              type=AlgorithmType.NN_LOCAL,
                              source=Source.THIRD_PARTY,
                              comment='comment-2',
                              created_at=datetime(2012, 1, 14, 12, 0, 5),
                              updated_at=datetime(2012, 1, 16, 12, 0, 5))
            algo3 = Algorithm(id=3,
                              algorithm_project_id=1,
                              project_id=1,
                              name='algo-3',
                              uuid='algo-uuid-3',
                              version=3,
                              publish_status=PublishStatus.UNPUBLISHED,
                              type=AlgorithmType.TREE_VERTICAL,
                              source=Source.UNSPECIFIED,
                              comment='comment-3',
                              created_at=datetime(2012, 1, 14, 12, 0, 5),
                              updated_at=datetime(2012, 1, 14, 12, 0, 5))
            algo4 = Algorithm(id=4,
                              algorithm_project_id=2,
                              project_id=1,
                              name='algo-4',
                              uuid='algo-uuid-4',
                              version=4,
                              publish_status=PublishStatus.PUBLISHED,
                              type=AlgorithmType.NN_VERTICAL,
                              source=Source.USER,
                              comment='comment-4',
                              created_at=datetime(2012, 1, 14, 12, 0, 5),
                              updated_at=datetime(2012, 1, 14, 12, 0, 5))
            algo5 = Algorithm(id=5,
                              algorithm_project_id=3,
                              project_id=1,
                              name='algo-5',
                              uuid='algo-uuid-5',
                              version=5,
                              publish_status=PublishStatus.UNPUBLISHED,
                              type=AlgorithmType.NN_VERTICAL,
                              source=Source.USER,
                              comment='comment-5',
                              created_at=datetime(2012, 1, 14, 12, 0, 5),
                              updated_at=datetime(2012, 1, 14, 12, 0, 5))
            algo6 = Algorithm(id=6,
                              algorithm_project_id=4,
                              project_id=2,
                              name='algo-6',
                              uuid='algo-uuid-6',
                              version=4,
                              publish_status=PublishStatus.PUBLISHED,
                              type=AlgorithmType.NN_LOCAL,
                              source=Source.THIRD_PARTY,
                              comment='comment-6',
                              created_at=datetime(2012, 1, 14, 12, 0, 5),
                              updated_at=datetime(2012, 1, 14, 12, 0, 5))
            parameter = ParseDict({'variables': [{'name': 'BATCH_SIZE', 'value': '128'}]}, AlgorithmParameter())
            algo1.set_parameter(parameter)
            session.add_all([
                project1, project2, algo_project1, algo_project2, algo_project3, algo_project4, algo1, algo2, algo3,
                algo4, algo5, algo6
            ])
            session.commit()

    def tearDown(self):
        self._channel.close()
        self._server.stop(5)
        return super().tearDown()

    @patch('fedlearner_webconsole.rpc.v2.resource_service_server.get_grpc_context_info')
    def test_list_algorithm_projects(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        resp = self._stub.ListAlgorithmProjects(ListAlgorithmProjectsRequest())
        algorithm_projects = sorted(resp.algorithm_projects, key=lambda x: x.uuid)
        self.assertEqual(len(algorithm_projects), 2)
        self.assertEqual(algorithm_projects[0].uuid, 'algo-project-uuid-1')
        self.assertEqual(algorithm_projects[0].type, 'NN_LOCAL')
        self.assertEqual(algorithm_projects[0].source, 'USER')
        self.assertEqual(algorithm_projects[0].updated_at, to_timestamp(datetime(2012, 1, 16, 12, 0, 5)))
        self.assertEqual(algorithm_projects[1].uuid, 'algo-project-uuid-2')
        self.assertEqual(algorithm_projects[1].type, 'NN_VERTICAL')
        self.assertEqual(algorithm_projects[1].source, 'THIRD_PARTY')
        self.assertEqual(algorithm_projects[1].updated_at, to_timestamp(datetime(2012, 1, 14, 12, 0, 5)))

    @patch('fedlearner_webconsole.rpc.v2.resource_service_server.get_grpc_context_info')
    def test_list_algorithm_project_with_filter_exp(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        filter_exp = parse_expression('(name~="1")')
        resp = self._stub.ListAlgorithmProjects(ListAlgorithmProjectsRequest(filter_exp=filter_exp))
        self.assertEqual(len(resp.algorithm_projects), 1)
        algo_project = resp.algorithm_projects[0]
        self.assertEqual(algo_project.uuid, 'algo-project-uuid-1')
        self.assertEqual(algo_project.type, 'NN_LOCAL')
        self.assertEqual(algo_project.source, 'USER')
        filter_exp = parse_expression('(type:["NN_VERTICAL"])')
        resp = self._stub.ListAlgorithmProjects(ListAlgorithmProjectsRequest(filter_exp=filter_exp))
        self.assertEqual((len(resp.algorithm_projects)), 1)
        algo_project = resp.algorithm_projects[0]
        self.assertEqual(algo_project.uuid, 'algo-project-uuid-2')
        self.assertEqual(algo_project.source, 'THIRD_PARTY')

    @patch('fedlearner_webconsole.rpc.v2.resource_service_server.get_grpc_context_info')
    def test_list_algorithms(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        resp = self._stub.ListAlgorithms(ListAlgorithmsRequest(algorithm_project_uuid='algo-project-uuid-1'))
        algorithms = resp.algorithms
        self.assertEqual(len(algorithms), 2)
        self.assertEqual(algorithms[0].uuid, 'algo-uuid-1')
        self.assertEqual(algorithms[1].uuid, 'algo-uuid-2')
        self.assertEqual(algorithms[0].type, 'NN_VERTICAL')
        self.assertEqual(algorithms[1].source, 'THIRD_PARTY')

    @patch('fedlearner_webconsole.rpc.v2.resource_service_server.get_grpc_context_info')
    def test_list_algorithms_with_wrong_algorithm_project_uuid(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.ListAlgorithms(ListAlgorithmsRequest(algorithm_project_uuid='algo-project-uuid-5'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)

    @patch('fedlearner_webconsole.rpc.v2.resource_service_server.get_grpc_context_info')
    def test_get_algorithm_project(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        resp = self._stub.GetAlgorithmProject(GetAlgorithmProjectRequest(algorithm_project_uuid='algo-project-uuid-1'))
        self.assertEqual(resp.type, 'NN_LOCAL')
        self.assertEqual(resp.source, 'USER')

    @patch('fedlearner_webconsole.rpc.v2.resource_service_server.get_grpc_context_info')
    def test_get_algorithm_project_with_wrong_uuid(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with self.assertRaises(grpc.RpcError) as cm:
            resp = self._stub.GetAlgorithmProject(GetAlgorithmProjectRequest(algorithm_project_uuid='1'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)

    @patch('fedlearner_webconsole.rpc.v2.resource_service_server.get_grpc_context_info')
    def test_get_unpublished_algorithm_project(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with self.assertRaises(grpc.RpcError) as cm:
            resp = self._stub.GetAlgorithmProject(
                GetAlgorithmProjectRequest(algorithm_project_uuid='algo-project-uuid-3'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.PERMISSION_DENIED)

    def test_get_algorithm_files_with_wrong_algorithm_uuid(self):
        with self.assertRaises(grpc.RpcError) as cm:
            resp = self._stub.GetAlgorithmFiles(GetAlgorithmFilesRequest(algorithm_uuid='algo-uuid-7'))
            # Grpc error cannot be thrown if no iterating when the rpc is streaming
            for _ in resp:
                pass
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)

    def test_get_algorithm_with_unpublished_algorithm(self):
        with self.assertRaises(grpc.RpcError) as cm:
            resp = self._stub.GetAlgorithm(GetAlgorithmRequest(algorithm_uuid='algo-uuid-3'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.PERMISSION_DENIED)

    def test_get_algorithm(self):
        resp = self._stub.GetAlgorithm(GetAlgorithmRequest(algorithm_uuid='algo-uuid-1'))
        self.assertEqual(resp.uuid, 'algo-uuid-1')
        self.assertEqual(resp.name, 'algo-1')
        self.assertEqual(resp.type, 'NN_VERTICAL')
        self.assertEqual(resp.source, 'USER')
        self.assertEqual(resp.version, 1)

    def test_get_algorithm_files(self):
        data_iterator = self._stub.GetAlgorithmFiles(GetAlgorithmFilesRequest(algorithm_uuid='algo-uuid-1'))
        resps = list(data_iterator)
        self.assertEqual(len(resps), 1)
        self.assertEqual(resps[0].hash, 'd41d8cd98f00b204e9800998ecf8427e')

    @patch('fedlearner_webconsole.rpc.v2.resource_service_server.get_pure_domain_from_context')
    @patch('fedlearner_webconsole.rpc.v2.resource_service_server.get_grpc_context_info')
    def test_inform_dataset(self, mock_get_grpc_context_info: MagicMock, mock_get_pure_domain_from_context: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        participant_domain_name = 'test participant'
        mock_get_pure_domain_from_context.return_value = participant_domain_name
        # test not_found
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.InformDataset(InformDatasetRequest(uuid='dataset uuid', auth_status='AUTHORIZED'))
            self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)

        # test invalidate participant
        with db.session_scope() as session:
            dataset = Dataset(id=1,
                              uuid='dataset uuid',
                              name='default dataset',
                              dataset_type=DatasetType.PSI,
                              comment='test comment',
                              path='/data/dataset/123',
                              project_id=1,
                              dataset_kind=DatasetKindV2.RAW,
                              is_published=True,
                              auth_status=AuthStatus.PENDING)
            session.add(dataset)
            dataset_job = DatasetJob(id=1,
                                     uuid='dataset_job uuid',
                                     project_id=1,
                                     input_dataset_id=0,
                                     output_dataset_id=1,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     state=DatasetJobState.PENDING,
                                     coordinator_id=1)
            session.add(dataset_job)
            session.commit()
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.InformDataset(InformDatasetRequest(uuid='dataset uuid', auth_status='AUTHORIZED'))
            self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)

        # test pass
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(1)
            participants_info = ParticipantsInfo(
                participants_map={participant_domain_name: ParticipantInfo(auth_status='PENDING')})
            dataset.set_participants_info(participants_info=participants_info)
            session.commit()
        self._stub.InformDataset(InformDatasetRequest(uuid='dataset uuid', auth_status='AUTHORIZED'))
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(1)
            participants_info = dataset.get_participants_info()
            self.assertEqual(participants_info.participants_map[participant_domain_name].auth_status, 'AUTHORIZED')

    @patch('fedlearner_webconsole.rpc.v2.resource_service_server.get_grpc_context_info')
    def test_list_datasets(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with db.session_scope() as session:
            dataset_job_1 = DatasetJob(id=1,
                                       uuid='dataset_job_1',
                                       project_id=1,
                                       input_dataset_id=0,
                                       output_dataset_id=1,
                                       kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                       state=DatasetJobState.PENDING,
                                       coordinator_id=1)
            session.add(dataset_job_1)
            dataset_1 = Dataset(id=1,
                                uuid='dataset_1 uuid',
                                name='default dataset 1',
                                dataset_type=DatasetType.PSI,
                                comment='test comment',
                                path='/data/dataset/123',
                                project_id=1,
                                dataset_kind=DatasetKindV2.RAW,
                                is_published=True)
            session.add(dataset_1)
            dataset_job_2 = DatasetJob(id=2,
                                       uuid='dataset_job_2',
                                       project_id=1,
                                       input_dataset_id=0,
                                       output_dataset_id=2,
                                       kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                       state=DatasetJobState.SUCCEEDED,
                                       coordinator_id=1,
                                       time_range=timedelta(days=1))
            session.add(dataset_job_2)
            dataset_2 = Dataset(id=2,
                                uuid='dataset_2 uuid',
                                name='default dataset 2',
                                dataset_type=DatasetType.PSI,
                                comment='test comment',
                                path='/data/dataset/123',
                                project_id=1,
                                dataset_kind=DatasetKindV2.PROCESSED,
                                is_published=True)
            session.add(dataset_2)
            session.commit()

        # test no filter
        expected_response = {
            'participant_datasets': [{
                'uuid': 'dataset_2 uuid',
                'name': 'default dataset 2',
                'format': 'TABULAR',
                'updated_at': ANY,
                'dataset_kind': 'PROCESSED',
                'dataset_type': 'PSI',
                'auth_status': 'PENDING',
                'project_id': ANY,
                'participant_id': ANY,
                'file_size': 0,
                'value': 0
            }, {
                'uuid': 'dataset_1 uuid',
                'name': 'default dataset 1',
                'format': 'TABULAR',
                'updated_at': ANY,
                'dataset_kind': 'RAW',
                'dataset_type': 'PSI',
                'auth_status': 'PENDING',
                'project_id': ANY,
                'participant_id': ANY,
                'file_size': 0,
                'value': 0
            }]
        }
        resp = self._stub.ListDatasets(ListDatasetsRequest())
        self.assertEqual(to_dict(resp), expected_response)

        # test with filter
        expected_response = {
            'participant_datasets': [{
                'uuid': 'dataset_2 uuid',
                'name': 'default dataset 2',
                'format': 'TABULAR',
                'updated_at': ANY,
                'dataset_kind': 'PROCESSED',
                'dataset_type': 'PSI',
                'auth_status': 'PENDING',
                'project_id': ANY,
                'participant_id': ANY,
                'file_size': 0,
                'value': 0
            }]
        }
        resp = self._stub.ListDatasets(
            ListDatasetsRequest(uuid='dataset_2 uuid',
                                kind=DatasetKindV2.PROCESSED.name,
                                state=ResourceState.SUCCEEDED.name,
                                time_range=TimeRange(days=1)))
        self.assertEqual(to_dict(resp), expected_response)


if __name__ == '__main__':
    unittest.main()

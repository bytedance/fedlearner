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

from datetime import datetime
import unittest
import grpc
import grpc_testing
from google.protobuf.empty_pb2 import Empty
from google.protobuf.descriptor import ServiceDescriptor
from testing.rpc.client import RpcClientTestCase
from fedlearner_webconsole.proto.dataset_pb2 import DatasetJobConfig, DatasetJobGlobalConfigs, DatasetJobStage
from fedlearner_webconsole.proto.rpc.v2 import job_service_pb2
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.rpc.v2.job_service_client import JobServiceClient
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.mmgr.models import ModelJobType, GroupAutoUpdateStatus
from fedlearner_webconsole.dataset.models import DatasetJobSchedulerState
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobGlobalConfig, AlgorithmProjectList, ModelJobPb, ModelJobGroupPb
from fedlearner_webconsole.proto.rpc.v2.job_service_pb2 import CreateModelJobRequest, InformTrustedJobGroupRequest, \
    UpdateTrustedJobGroupRequest, DeleteTrustedJobGroupRequest, GetTrustedJobGroupRequest, \
    GetTrustedJobGroupResponse, CreateDatasetJobStageRequest, GetDatasetJobStageRequest, GetDatasetJobStageResponse, \
    CreateModelJobGroupRequest, GetModelJobRequest, GetModelJobGroupRequest, InformModelJobGroupRequest, \
    InformTrustedJobRequest, GetTrustedJobRequest, GetTrustedJobResponse, CreateTrustedExportJobRequest, \
    UpdateDatasetJobSchedulerStateRequest, UpdateModelJobGroupRequest, InformModelJobRequest

_SERVICE_DESCRIPTOR: ServiceDescriptor = job_service_pb2.DESCRIPTOR.services_by_name['JobService']


class JobServiceClientTest(RpcClientTestCase):

    def setUp(self):
        super().setUp()
        self._fake_channel: grpc_testing.Channel = grpc_testing.channel([_SERVICE_DESCRIPTOR],
                                                                        grpc_testing.strict_real_time())
        self._client = JobServiceClient(self._fake_channel)

    def test_inform_trusted_job_group(self):
        call = self.client_execution_pool.submit(self._client.inform_trusted_job_group,
                                                 uuid='uuid',
                                                 auth_status=AuthStatus.AUTHORIZED)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['InformTrustedJobGroup'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, InformTrustedJobGroupRequest(uuid='uuid', auth_status='AUTHORIZED'))
        self.assertEqual(call.result(), expected_response)

    def test_update_trusted_job_group(self):
        call = self.client_execution_pool.submit(self._client.update_trusted_job_group,
                                                 uuid='uuid',
                                                 algorithm_uuid='algorithm-uuid')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['UpdateTrustedJobGroup'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, UpdateTrustedJobGroupRequest(uuid='uuid', algorithm_uuid='algorithm-uuid'))
        self.assertEqual(call.result(), expected_response)

    def test_delete_trusted_job_group(self):
        call = self.client_execution_pool.submit(self._client.delete_trusted_job_group, uuid='uuid')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['DeleteTrustedJobGroup'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, DeleteTrustedJobGroupRequest(uuid='uuid'))
        self.assertEqual(call.result(), expected_response)

    def test_get_trusted_job_group(self):
        call = self.client_execution_pool.submit(self._client.get_trusted_job_group, uuid='uuid')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['GetTrustedJobGroup'])
        expected_response = GetTrustedJobGroupResponse(auth_status='AUTHORIZED')
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, GetTrustedJobGroupRequest(uuid='uuid'))
        self.assertEqual(call.result(), expected_response)

    def test_get_trusted_job(self):
        call = self.client_execution_pool.submit(self._client.get_trusted_job, uuid='uuid')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['GetTrustedJob'])
        expected_response = GetTrustedJobResponse(auth_status=AuthStatus.WITHDRAW.name)
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, GetTrustedJobRequest(uuid='uuid'))
        self.assertEqual(call.result(), expected_response)

    def test_get_model_job(self):
        call = self.client_execution_pool.submit(self._client.get_model_job, uuid='uuid')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['GetModelJob'])
        expected_response = ModelJobPb(name='name')
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, GetModelJobRequest(uuid='uuid'))
        self.assertEqual(call.result(), expected_response)

    def test_create_model_job(self):
        call = self.client_execution_pool.submit(self._client.create_model_job,
                                                 name='name',
                                                 uuid='uuid',
                                                 group_uuid='group_uuid',
                                                 model_job_type=ModelJobType.TRAINING,
                                                 algorithm_type=AlgorithmType.NN_VERTICAL,
                                                 global_config=ModelJobGlobalConfig(),
                                                 version=3)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['CreateModelJob'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(
            request,
            CreateModelJobRequest(name='name',
                                  uuid='uuid',
                                  group_uuid='group_uuid',
                                  model_job_type='TRAINING',
                                  algorithm_type='NN_VERTICAL',
                                  global_config=ModelJobGlobalConfig(),
                                  version=3))
        self.assertEqual(call.result(), expected_response)

    def test_inform_model_job(self):
        call = self.client_execution_pool.submit(self._client.inform_model_job,
                                                 uuid='uuid',
                                                 auth_status=AuthStatus.AUTHORIZED)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['InformModelJob'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, InformModelJobRequest(uuid='uuid', auth_status=AuthStatus.AUTHORIZED.name))
        self.assertEqual(call.result(), expected_response)

    def test_create_dataset_job_stage(self):
        event_time = datetime(2022, 1, 1)
        call = self.client_execution_pool.submit(self._client.create_dataset_job_stage,
                                                 dataset_job_uuid='dataset_job_uuid',
                                                 dataset_job_stage_uuid='dataset_job_stage_uuid',
                                                 name='20220101',
                                                 event_time=event_time)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['CreateDatasetJobStage'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(
            request,
            CreateDatasetJobStageRequest(
                dataset_job_uuid='dataset_job_uuid',
                dataset_job_stage_uuid='dataset_job_stage_uuid',
                name='20220101',
                event_time=to_timestamp(event_time),
            ))
        self.assertEqual(call.result(), expected_response)

        # test event_time is None
        call = self.client_execution_pool.submit(self._client.create_dataset_job_stage,
                                                 dataset_job_uuid='dataset_job_uuid',
                                                 dataset_job_stage_uuid='dataset_job_stage_uuid',
                                                 name='20220101',
                                                 event_time=None)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['CreateDatasetJobStage'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(
            request,
            CreateDatasetJobStageRequest(dataset_job_uuid='dataset_job_uuid',
                                         dataset_job_stage_uuid='dataset_job_stage_uuid',
                                         name='20220101'))
        self.assertEqual(call.result(), expected_response)

    def test_get_dataset_job_stage(self):
        call = self.client_execution_pool.submit(self._client.get_dataset_job_stage,
                                                 dataset_job_stage_uuid='dataset_job_stage_uuid')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['GetDatasetJobStage'])
        dataset_job_stage = DatasetJobStage(
            id=1,
            uuid='fake stage uuid',
            name='test_dataset_job_stage',
            dataset_job_uuid='fake job uuid',
            global_configs=DatasetJobGlobalConfigs(
                global_configs={'test_domain': DatasetJobConfig(dataset_uuid='dataset uuid', variables=[])}),
            workflow_definition=WorkflowDefinition(group_alias='fake template', variables=[], job_definitions=[]))
        expected_response = GetDatasetJobStageResponse(dataset_job_stage=dataset_job_stage)
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, GetDatasetJobStageRequest(dataset_job_stage_uuid='dataset_job_stage_uuid'))
        self.assertEqual(call.result(), expected_response)

    def test_update_dataset_job_scheduler_state(self):
        call = self.client_execution_pool.submit(self._client.update_dataset_job_scheduler_state,
                                                 uuid='dataset_job_uuid',
                                                 scheduler_state=DatasetJobSchedulerState.RUNNABLE)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['UpdateDatasetJobSchedulerState'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request,
                         UpdateDatasetJobSchedulerStateRequest(
                             uuid='dataset_job_uuid',
                             scheduler_state='RUNNABLE',
                         ))
        self.assertEqual(call.result(), expected_response)

    def test_get_model_job_group(self):
        call = self.client_execution_pool.submit(self._client.get_model_job_group, uuid='uuid')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['GetModelJobGroup'])
        expected_response = ModelJobGroupPb(name='12')
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, GetModelJobGroupRequest(uuid='uuid'))
        self.assertEqual(call.result(), expected_response)

    def test_inform_model_job_group(self):
        call = self.client_execution_pool.submit(self._client.inform_model_job_group,
                                                 uuid='uuid',
                                                 auth_status=AuthStatus.AUTHORIZED)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['InformModelJobGroup'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, InformModelJobGroupRequest(uuid='uuid', auth_status=AuthStatus.AUTHORIZED.name))
        self.assertEqual(call.result(), expected_response)

    def test_update_model_job_group(self):
        call = self.client_execution_pool.submit(self._client.update_model_job_group,
                                                 uuid='uuid',
                                                 auto_update_status=GroupAutoUpdateStatus.ACTIVE,
                                                 start_dataset_job_stage_uuid='stage_uuid')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['UpdateModelJobGroup'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(
            request,
            UpdateModelJobGroupRequest(uuid='uuid',
                                       auto_update_status=GroupAutoUpdateStatus.ACTIVE.name,
                                       start_dataset_job_stage_uuid='stage_uuid'))
        self.assertEqual(call.result(), expected_response)
        call = self.client_execution_pool.submit(self._client.update_model_job_group,
                                                 uuid='uuid',
                                                 auto_update_status=GroupAutoUpdateStatus.STOPPED)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['UpdateModelJobGroup'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(
            request,
            UpdateModelJobGroupRequest(uuid='uuid',
                                       auto_update_status=GroupAutoUpdateStatus.STOPPED.name,
                                       start_dataset_job_stage_uuid=None))
        self.assertEqual(call.result(), expected_response)
        call = self.client_execution_pool.submit(self._client.update_model_job_group, uuid='uuid')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['UpdateModelJobGroup'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(
            request, UpdateModelJobGroupRequest(uuid='uuid', auto_update_status=None,
                                                start_dataset_job_stage_uuid=None))
        self.assertEqual(call.result(), expected_response)

    def test_create_model_job_group(self):
        call = self.client_execution_pool.submit(
            self._client.create_model_job_group,
            name='name',
            uuid='uuid',
            algorithm_type=AlgorithmType.NN_VERTICAL,
            dataset_uuid='uuid',
            algorithm_project_list=AlgorithmProjectList(algorithm_projects={'test': 'uuid'}))
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['CreateModelJobGroup'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(
            request,
            CreateModelJobGroupRequest(
                name='name',
                uuid='uuid',
                algorithm_type='NN_VERTICAL',
                dataset_uuid='uuid',
                algorithm_project_list=AlgorithmProjectList(algorithm_projects={'test': 'uuid'})))
        self.assertEqual(call.result(), expected_response)

    def test_inform_trusted_job(self):
        call = self.client_execution_pool.submit(self._client.inform_trusted_job,
                                                 uuid='uuid',
                                                 auth_status=AuthStatus.AUTHORIZED)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['InformTrustedJob'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, InformTrustedJobRequest(uuid='uuid', auth_status=AuthStatus.AUTHORIZED.name))
        self.assertEqual(call.result(), expected_response)

    def test_create_trusted_export_job(self):
        call = self.client_execution_pool.submit(self._client.create_trusted_export_job,
                                                 uuid='uuid1',
                                                 name='V1-domain1-1',
                                                 export_count=1,
                                                 parent_uuid='uuid2',
                                                 ticket_uuid='ticket uuid')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['CreateTrustedExportJob'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(
            request,
            CreateTrustedExportJobRequest(uuid='uuid1',
                                          name='V1-domain1-1',
                                          export_count=1,
                                          parent_uuid='uuid2',
                                          ticket_uuid='ticket uuid'))
        self.assertEqual(call.result(), expected_response)


if __name__ == '__main__':
    unittest.main()

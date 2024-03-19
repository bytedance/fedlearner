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
from envs import Envs
from typing import Iterable, Optional
from google.protobuf import empty_pb2

from fedlearner_webconsole.rpc.v2.client_base import ParticipantProjectRpcClient
from fedlearner_webconsole.dataset.models import DatasetKindV2, ResourceState
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression
from fedlearner_webconsole.proto.rpc.v2.resource_service_pb2_grpc import ResourceServiceStub
from fedlearner_webconsole.proto.rpc.v2.resource_service_pb2 import GetAlgorithmRequest, GetAlgorithmProjectRequest, \
    InformDatasetRequest, ListAlgorithmProjectsRequest, ListAlgorithmProjectsResponse, ListAlgorithmsRequest, \
    ListAlgorithmsResponse, GetAlgorithmFilesRequest, GetAlgorithmFilesResponse, ListDatasetsRequest, \
    ListDatasetsResponse
from fedlearner_webconsole.proto.dataset_pb2 import TimeRange
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmProjectPb, AlgorithmPb
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.decorators.retry import retry_fn


def _need_retry_for_get(err: Exception) -> bool:
    if not isinstance(err, grpc.RpcError):
        return False
    # No need to retry for NOT_FOUND and PERMISSION_DENIED
    if err.code() == grpc.StatusCode.NOT_FOUND or err.code() == grpc.StatusCode.PERMISSION_DENIED:
        return False
    return True


def _default_need_retry(err: Exception) -> bool:
    return isinstance(err, grpc.RpcError)


class ResourceServiceClient(ParticipantProjectRpcClient):

    def __init__(self, channel: grpc.Channel):
        super().__init__(channel)
        self._stub: ResourceServiceStub = ResourceServiceStub(channel)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def list_algorithm_projects(self, filter_exp: Optional[FilterExpression] = None) -> ListAlgorithmProjectsResponse:
        request = ListAlgorithmProjectsRequest(filter_exp=filter_exp)
        return self._stub.ListAlgorithmProjects(request=request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_get)
    def get_algorithm_project(self, algorithm_project_uuid: str) -> AlgorithmProjectPb:
        request = GetAlgorithmProjectRequest(algorithm_project_uuid=algorithm_project_uuid)
        return self._stub.GetAlgorithmProject(request=request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def list_algorithms(self, algorithm_project_uuid: str) -> ListAlgorithmsResponse:
        request = ListAlgorithmsRequest(algorithm_project_uuid=algorithm_project_uuid)
        return self._stub.ListAlgorithms(request=request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_get)
    def get_algorithm(self, algorithm_uuid: str) -> AlgorithmPb:
        request = GetAlgorithmRequest(algorithm_uuid=algorithm_uuid)
        return self._stub.GetAlgorithm(request=request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_get)
    def get_algorithm_files(self, algorithm_uuid: str) -> Iterable[GetAlgorithmFilesResponse]:
        request = GetAlgorithmFilesRequest(algorithm_uuid=algorithm_uuid)
        return self._stub.GetAlgorithmFiles(request=request, timeout=Envs.GRPC_STREAM_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def inform_dataset(self, dataset_uuid: str, auth_status: AuthStatus) -> empty_pb2.Empty:
        request = InformDatasetRequest(uuid=dataset_uuid, auth_status=auth_status.name)
        return self._stub.InformDataset(request=request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def list_datasets(self,
                      kind: Optional[DatasetKindV2] = None,
                      uuid: Optional[str] = None,
                      state: Optional[ResourceState] = None,
                      time_range: Optional[TimeRange] = None) -> ListDatasetsResponse:
        request = ListDatasetsRequest()
        if kind is not None:
            request.kind = kind.name
        if uuid is not None:
            request.uuid = uuid
        if state is not None:
            request.state = state.name
        if time_range is not None:
            request.time_range.MergeFrom(time_range)
        return self._stub.ListDatasets(request=request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

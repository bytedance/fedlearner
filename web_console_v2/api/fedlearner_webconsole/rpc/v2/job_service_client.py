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
from datetime import datetime
from google.protobuf import empty_pb2
from typing import Optional

from envs import Envs
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.decorators.retry import retry_fn
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.proto.rpc.v2.job_service_pb2_grpc import JobServiceStub
from fedlearner_webconsole.rpc.v2.client_base import ParticipantProjectRpcClient
from fedlearner_webconsole.mmgr.models import ModelJobType, AlgorithmType, GroupAutoUpdateStatus
from fedlearner_webconsole.dataset.models import DatasetJobSchedulerState
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobGlobalConfig, AlgorithmProjectList, ModelJobPb, ModelJobGroupPb
from fedlearner_webconsole.proto.rpc.v2.job_service_pb2 import CreateModelJobRequest, InformTrustedJobGroupRequest, \
    UpdateTrustedJobGroupRequest, DeleteTrustedJobGroupRequest, GetTrustedJobGroupRequest, \
    GetTrustedJobGroupResponse, CreateDatasetJobStageRequest, GetDatasetJobStageRequest, GetDatasetJobStageResponse, \
    CreateModelJobGroupRequest, GetModelJobRequest, GetModelJobGroupRequest, InformModelJobGroupRequest, \
    InformTrustedJobRequest, GetTrustedJobRequest, GetTrustedJobResponse, CreateTrustedExportJobRequest, \
    UpdateDatasetJobSchedulerStateRequest, UpdateModelJobGroupRequest, InformModelJobRequest


def _need_retry_for_get(err: Exception) -> bool:
    if not isinstance(err, grpc.RpcError):
        return False
    # No need to retry for NOT_FOUND
    return err.code() != grpc.StatusCode.NOT_FOUND


def _need_retry_for_create(err: Exception) -> bool:
    if not isinstance(err, grpc.RpcError):
        return False
    # No need to retry for INVALID_ARGUMENT
    return err.code() != grpc.StatusCode.INVALID_ARGUMENT


def _default_need_retry(err: Exception) -> bool:
    return isinstance(err, grpc.RpcError)


class JobServiceClient(ParticipantProjectRpcClient):

    def __init__(self, channel: grpc.Channel):
        super().__init__(channel)
        self._stub: JobServiceStub = JobServiceStub(channel)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_get)
    def inform_trusted_job_group(self, uuid: str, auth_status: AuthStatus) -> empty_pb2.Empty:
        msg = InformTrustedJobGroupRequest(uuid=uuid, auth_status=auth_status.name)
        return self._stub.InformTrustedJobGroup(request=msg, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_get)
    def update_trusted_job_group(self, uuid: str, algorithm_uuid: str) -> empty_pb2.Empty:
        msg = UpdateTrustedJobGroupRequest(uuid=uuid, algorithm_uuid=algorithm_uuid)
        return self._stub.UpdateTrustedJobGroup(request=msg, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def delete_trusted_job_group(self, uuid: str) -> empty_pb2.Empty:
        msg = DeleteTrustedJobGroupRequest(uuid=uuid)
        return self._stub.DeleteTrustedJobGroup(request=msg, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_get)
    def get_trusted_job_group(self, uuid: str) -> GetTrustedJobGroupResponse:
        msg = GetTrustedJobGroupRequest(uuid=uuid)
        return self._stub.GetTrustedJobGroup(request=msg, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_create)
    def create_trusted_export_job(self, uuid: str, name: str, export_count: int, parent_uuid: str,
                                  ticket_uuid: str) -> empty_pb2.Empty:
        msg = CreateTrustedExportJobRequest(uuid=uuid,
                                            name=name,
                                            export_count=export_count,
                                            parent_uuid=parent_uuid,
                                            ticket_uuid=ticket_uuid)
        return self._stub.CreateTrustedExportJob(request=msg, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_get)
    def get_model_job(self, uuid: str) -> ModelJobPb:
        return self._stub.GetModelJob(request=GetModelJobRequest(uuid=uuid), timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def create_model_job(self, name: str, uuid: str, group_uuid: str, model_job_type: ModelJobType,
                         algorithm_type: AlgorithmType, global_config: ModelJobGlobalConfig,
                         version: int) -> empty_pb2.Empty:
        request = CreateModelJobRequest(name=name,
                                        uuid=uuid,
                                        group_uuid=group_uuid,
                                        model_job_type=model_job_type.name,
                                        algorithm_type=algorithm_type.name,
                                        global_config=global_config,
                                        version=version)
        return self._stub.CreateModelJob(request=request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def inform_model_job(self, uuid: str, auth_status: AuthStatus) -> empty_pb2.Empty:
        msg = InformModelJobRequest(uuid=uuid, auth_status=auth_status.name)
        return self._stub.InformModelJob(request=msg, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_get)
    def get_model_job_group(self, uuid: str) -> ModelJobGroupPb:
        return self._stub.GetModelJobGroup(request=GetModelJobGroupRequest(uuid=uuid), timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def inform_model_job_group(self, uuid: str, auth_status: AuthStatus) -> empty_pb2.Empty:
        msg = InformModelJobGroupRequest(uuid=uuid, auth_status=auth_status.name)
        return self._stub.InformModelJobGroup(request=msg, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def update_model_job_group(self,
                               uuid: str,
                               auto_update_status: Optional[GroupAutoUpdateStatus] = None,
                               start_dataset_job_stage_uuid: Optional[str] = None) -> empty_pb2.Empty:
        msg = UpdateModelJobGroupRequest(uuid=uuid,
                                         auto_update_status=auto_update_status.name if auto_update_status else None,
                                         start_dataset_job_stage_uuid=start_dataset_job_stage_uuid)
        return self._stub.UpdateModelJobGroup(request=msg, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_create)
    def create_dataset_job_stage(self,
                                 dataset_job_uuid: str,
                                 dataset_job_stage_uuid: str,
                                 name: str,
                                 event_time: Optional[datetime] = None) -> empty_pb2.Empty:
        request = CreateDatasetJobStageRequest(dataset_job_uuid=dataset_job_uuid,
                                               dataset_job_stage_uuid=dataset_job_stage_uuid,
                                               name=name,
                                               event_time=to_timestamp(event_time) if event_time else None)
        return self._stub.CreateDatasetJobStage(request=request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_get)
    def get_dataset_job_stage(self, dataset_job_stage_uuid: str) -> GetDatasetJobStageResponse:
        msg = GetDatasetJobStageRequest(dataset_job_stage_uuid=dataset_job_stage_uuid)
        return self._stub.GetDatasetJobStage(request=msg, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_create)
    def update_dataset_job_scheduler_state(self, uuid: str,
                                           scheduler_state: DatasetJobSchedulerState) -> empty_pb2.Empty:
        request = UpdateDatasetJobSchedulerStateRequest(uuid=uuid, scheduler_state=scheduler_state.name)
        return self._stub.UpdateDatasetJobSchedulerState(request=request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_create)
    def create_model_job_group(self, name: str, uuid: str, algorithm_type: AlgorithmType, dataset_uuid: str,
                               algorithm_project_list: AlgorithmProjectList):
        request = CreateModelJobGroupRequest(name=name,
                                             uuid=uuid,
                                             algorithm_type=algorithm_type.name,
                                             dataset_uuid=dataset_uuid,
                                             algorithm_project_list=algorithm_project_list)
        return self._stub.CreateModelJobGroup(request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def inform_trusted_job(self, uuid: str, auth_status: AuthStatus) -> empty_pb2.Empty:
        msg = InformTrustedJobRequest(uuid=uuid, auth_status=auth_status.name)
        return self._stub.InformTrustedJob(request=msg, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_get)
    def get_trusted_job(self, uuid: str) -> GetTrustedJobResponse:
        msg = GetTrustedJobRequest(uuid=uuid)
        return self._stub.GetTrustedJob(request=msg, timeout=Envs.GRPC_CLIENT_TIMEOUT)

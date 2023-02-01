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

from typing import Dict

import grpc
from google.protobuf import empty_pb2

from envs import Envs
from fedlearner_webconsole.project.models import PendingProject, PendingProjectState
from fedlearner_webconsole.workflow_template.models import WorkflowTemplateKind
from fedlearner_webconsole.proto.project_pb2 import ParticipantInfo
from fedlearner_webconsole.proto.rpc.v2.project_service_pb2 import CreatePendingProjectRequest, \
    UpdatePendingProjectRequest, SyncPendingProjectStateRequest, CreateProjectRequest, DeletePendingProjectRequest, \
    SendTemplateRevisionRequest
from fedlearner_webconsole.proto.rpc.v2.project_service_pb2_grpc import ProjectServiceStub
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.rpc.v2.client_base import ParticipantRpcClient
from fedlearner_webconsole.utils.decorators.retry import retry_fn


# only unavailable is caused by network jitter.
def _retry_unavailable(err: Exception) -> bool:
    if not isinstance(err, grpc.RpcError):
        return False
    return err.code() == grpc.StatusCode.UNAVAILABLE


class ProjectServiceClient(ParticipantRpcClient):

    def __init__(self, channel: grpc.Channel):
        super().__init__(channel)
        self._stub: ProjectServiceStub = ProjectServiceStub(channel)

    @retry_fn(retry_times=3, need_retry=_retry_unavailable)
    def create_pending_project(self, pending_project: PendingProject) -> empty_pb2.Empty:
        request = CreatePendingProjectRequest(uuid=pending_project.uuid,
                                              name=pending_project.name,
                                              participants_info=pending_project.get_participants_info(),
                                              comment=pending_project.comment,
                                              creator_username=pending_project.creator_username,
                                              config=pending_project.get_config(),
                                              ticket_uuid=pending_project.ticket_uuid)
        return self._stub.CreatePendingProject(request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_retry_unavailable)
    def update_pending_project(self, uuid: str, participants_map: Dict[str, ParticipantInfo]) -> empty_pb2.Empty:
        request = UpdatePendingProjectRequest(uuid=uuid, participants_map=participants_map)
        return self._stub.UpdatePendingProject(request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_retry_unavailable)
    def create_project(self, uuid: str):
        request = CreateProjectRequest(uuid=uuid)
        return self._stub.CreateProject(request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_retry_unavailable)
    def sync_pending_project_state(self, uuid: str, state: PendingProjectState) -> empty_pb2.Empty:
        request = SyncPendingProjectStateRequest(uuid=uuid, state=state.name)
        return self._stub.SyncPendingProjectState(request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_retry_unavailable)
    def delete_pending_project(self, uuid: str):
        request = DeletePendingProjectRequest(uuid=uuid)
        return self._stub.DeletePendingProject(request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_retry_unavailable)
    def send_template_revision(self, config: WorkflowDefinition, name: str, comment: str, kind: WorkflowTemplateKind,
                               revision_index: int):
        request = SendTemplateRevisionRequest(config=config,
                                              name=name,
                                              comment=comment,
                                              kind=kind.name,
                                              revision_index=revision_index)
        return self._stub.SendTemplateRevision(request, timeout=Envs.GRPC_CLIENT_TIMEOUT)

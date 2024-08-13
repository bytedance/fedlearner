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

from typing import Callable, Dict, NamedTuple

import grpc
from google.protobuf.empty_pb2 import Empty
from google.protobuf.message import Message

from fedlearner_webconsole.participant.models import ParticipantType
from fedlearner_webconsole.project.models import PendingProject, ProjectRole, PendingProjectState
from fedlearner_webconsole.rpc.v2.project_service_client import ProjectServiceClient


class ParticipantResp(NamedTuple):
    succeeded: bool
    resp: Message
    msg: str


def _get_domain_name(pure_domain_name: str) -> str:
    """Get domain name from pure_domain_name

    Args:
        pure_domain_name (str): pure_domain_name

    Returns:
        str: domain name, like fl-ali-test.com
    """
    return f'fl-{pure_domain_name}.com'


def _get_resp(pure_domain_name: str, method: Callable) -> ParticipantResp:
    client = ProjectServiceClient.from_participant(_get_domain_name(pure_domain_name))
    try:
        resp = ParticipantResp(True, method(client), '')
    except grpc.RpcError as e:
        resp = ParticipantResp(False, Empty(), str(e))
    return resp


class PendingProjectRpcController(object):
    """A helper to Send Grpc request via participants_info in pending project."""

    def __init__(self, pending_project: PendingProject = None):
        self._pending_project = pending_project

    def send_to_participants(self, method: Callable) -> Dict[str, ParticipantResp]:
        if self._pending_project.role == ProjectRole.PARTICIPANT:
            # when a project is in pending the proxy should not be supported,
            # which participant used to connect to others via coordinator.
            raise ValueError('participant cant connect to participant in pending project')
        resp_map = {}
        for pure_domain_name, p_info in self._pending_project.get_participants_info().participants_map.items():
            if p_info.role == ProjectRole.COORDINATOR.name or p_info.type == ParticipantType.LIGHT_CLIENT.name:
                continue

            resp_map[pure_domain_name] = _get_resp(pure_domain_name, method)
        return resp_map

    def sync_pending_project_state_to_coordinator(self, uuid: str, state: PendingProjectState) -> ParticipantResp:
        assert self._pending_project.role == ProjectRole.PARTICIPANT
        pure_domain, _ = self._pending_project.get_coordinator_info()
        return _get_resp(pure_domain,
                         lambda client: ProjectServiceClient.sync_pending_project_state(client, uuid, state))

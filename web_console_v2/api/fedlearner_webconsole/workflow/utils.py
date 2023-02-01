# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
from typing import List, Optional

from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.exceptions import InternalException
from fedlearner_webconsole.utils.metrics import emit_store
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.proto.common_pb2 import CreateJobFlag
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.workflow_definition_pb2 import \
    WorkflowDefinition


def is_local(config: WorkflowDefinition, job_flags: Optional[List[int]] = None) -> bool:
    # if self.config is None, it must be created by the opposite side
    if config is None:
        return False
    # since _setup_jobs has not been called, job_definitions is used
    job_defs = config.job_definitions
    if job_flags is None:
        num_jobs = len(job_defs)
        job_flags = [common_pb2.CreateJobFlag.NEW] * num_jobs
    for i, (job_def, flag) in enumerate(zip(job_defs, job_flags)):
        if flag != CreateJobFlag.REUSE and job_def.is_federated:
            return False
    return True


def is_peer_job_inheritance_matched(project: Project, workflow_definition: WorkflowDefinition, job_flags: List[int],
                                    peer_job_flags: List[int], parent_uuid: str, parent_name: str,
                                    participants: List) -> bool:
    """Checks if the job inheritance is matched with peer workflow.

    We should make sure the federated jobs should have the same job flag
    (inherit from parent or not)."""
    # TODO(hangweiqiang): Fix for multi-peer
    client = RpcClient.from_project_and_participant(project.name, project.token, participants[0].domain_name)
    # Gets peer parent workflow
    resp = client.get_workflow(parent_uuid, parent_name)
    if resp.status.code != common_pb2.STATUS_SUCCESS:
        emit_store('get_peer_workflow_failed', 1)
        raise InternalException(resp.status.msg)
    job_defs = workflow_definition.job_definitions
    peer_job_defs = resp.config.job_definitions
    for i, job_def in enumerate(job_defs):
        if job_def.is_federated:
            for j, peer_job_def in enumerate(peer_job_defs):
                if job_def.name == peer_job_def.name:
                    if job_flags[i] != peer_job_flags[j]:
                        return False
    return True

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

import logging
from typing import List

from sqlalchemy.orm import Session

from fedlearner_webconsole.db import db
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.two_pc.transaction_manager import TransactionManager
from fedlearner_webconsole.proto.two_pc_pb2 import (TwoPcType, TransactionData, TransitWorkflowStateData)
from fedlearner_webconsole.exceptions import InternalException, InvalidArgumentException
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.workflow.workflow_controller import start_workflow_locally, stop_workflow_locally, \
    invalidate_workflow_locally


def _change_workflow_status(target_state: WorkflowState, project: Project, uuid: str, participants_domain_name: List):
    assert target_state in (WorkflowState.RUNNING, WorkflowState.STOPPED)
    tm = TransactionManager(project_name=project.name,
                            project_token=project.token,
                            participants=participants_domain_name,
                            two_pc_type=TwoPcType.CONTROL_WORKFLOW_STATE)
    data = TransitWorkflowStateData(target_state=target_state.name, workflow_uuid=uuid)
    successed, message = tm.run(data=TransactionData(transit_workflow_state_data=data))
    if not successed:
        raise InternalException(f'error when converting workflow state by 2PC: {message}')


def _start_2pc_workflow(project: Project, uuid: str, participants_domain_name: List):
    return _change_workflow_status(WorkflowState.RUNNING, project, uuid, participants_domain_name)


def _stop_2pc_workflow(project: Project, uuid: str, participants_domain_name: List):
    return _change_workflow_status(WorkflowState.STOPPED, project, uuid, participants_domain_name)


# start workflow main entry
def start_workflow(workflow_id: int):
    # TODO(liuhehan): add uuid as entrypoint
    with db.session_scope() as session:
        workflow = session.query(Workflow).filter_by(id=workflow_id).first()
        if workflow.is_local():
            # local entry
            try:
                # TODO(linfan.fine): gets rid of the session, the controller should be in a separate session
                start_workflow_locally(session, workflow)
                session.commit()
                return
            except RuntimeError as e:
                raise InternalException(e) from e
            except ValueError as e:
                raise InvalidArgumentException(str(e)) from e
        participants = ParticipantService(session).get_platform_participants_by_project(workflow.project.id)
        project = session.query(Project).filter_by(id=workflow.project.id).first()
        participants_domain_name = [participant.domain_name for participant in participants]
    # new version fed entry
    _start_2pc_workflow(project, workflow.uuid, participants_domain_name)


# stop workflow main entry
def stop_workflow(workflow_id: int):
    with db.session_scope() as session:
        workflow = session.query(Workflow).get(workflow_id)
        if workflow.is_local():
            # local entry
            try:
                # TODO(linfan.fine): gets rid of the session, the controller should be in a separate session
                stop_workflow_locally(session, workflow)
                session.commit()
                return
            except RuntimeError as e:
                raise InternalException(e) from e
        participants = ParticipantService(session).get_platform_participants_by_project(workflow.project.id)
        project = session.query(Project).filter_by(id=workflow.project.id).first()
        participants_domain_name = [participant.domain_name for participant in participants]
    # new version fed entry
    _stop_2pc_workflow(project, workflow.uuid, participants_domain_name)
    with db.session_scope() as session:
        workflow = session.query(Workflow).get(workflow_id)


def invalidate_workflow_job(session: Session, workflow: Workflow):
    """Invalidates workflow job across all participants."""
    invalidate_workflow_locally(session, workflow)
    if workflow.is_local():
        # No actions needed
        return

    service = ParticipantService(session)
    participants = service.get_platform_participants_by_project(workflow.project.id)
    # Invalidates peer's workflow
    for participant in participants:
        client = RpcClient.from_project_and_participant(workflow.project.name, workflow.project.token,
                                                        participant.domain_name)
        resp = client.invalidate_workflow(workflow.uuid)
        if not resp.succeeded:
            # Ignores those errors as it will be handled by their workflow schedulers
            logging.warning(
                f'failed to invalidate peer workflow, workflow id: {workflow.id}, participant name: {participant.name}')

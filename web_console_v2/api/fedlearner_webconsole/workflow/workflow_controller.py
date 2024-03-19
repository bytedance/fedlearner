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
from typing import Optional

from sqlalchemy.orm import Session

from fedlearner_webconsole.auth.services import UserService
from fedlearner_webconsole.job.controller import stop_job, schedule_job, \
    start_job_if_ready
from fedlearner_webconsole.notification.email import send_email
from fedlearner_webconsole.notification.template import NotificationTemplateName
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.utils import pp_datetime
from fedlearner_webconsole.utils.const import SYSTEM_WORKFLOW_CREATOR_USERNAME
from fedlearner_webconsole.utils.flask_utils import get_link
from fedlearner_webconsole.workflow.models import WorkflowState, Workflow, TransactionState
from fedlearner_webconsole.workflow.service import WorkflowService, CreateNewWorkflowParams, update_cronjob_config


# TODO(xiangyuxuan.prs): uses system workflow template revision instead of template directly
def create_ready_workflow(
    session: Session,
    name: str,
    config: WorkflowDefinition,
    project_id: int,
    uuid: str,
    template_id: Optional[int] = None,
    comment: Optional[str] = None,
) -> Workflow:
    """Creates a workflow in ready(configured) state, this is for our internal usage, such as dataset module.

    Args:
        session: DB session of the transaction.
        name: Workflow name.
        config: Workflow configurations.
        project_id: Which project this workflow belongs to.
        uuid: Global uinique id of this workflow, practicely we use it for pairing.
        template_id: Which template this workflow will use.
        comment: Optional comment of the workflow.
    """
    return WorkflowService(session).create_workflow(
        name=name,
        config=config,
        params=CreateNewWorkflowParams(project_id=project_id, template_id=template_id),
        uuid=uuid,
        comment=comment,
        creator_username=SYSTEM_WORKFLOW_CREATOR_USERNAME,
        state=WorkflowState.READY,
        target_state=WorkflowState.INVALID,
    )


def start_workflow_locally(session: Session, workflow: Workflow):
    """Starts the workflow locally, it does not affect other participants."""
    if not workflow.can_transit_to(WorkflowState.RUNNING):
        raise RuntimeError(f'invalid workflow state {workflow.state} when try to start')
    is_valid, info = WorkflowService(session).validate_workflow(workflow)
    if not is_valid:
        job_name, validate_e = info
        raise ValueError(f'Invalid Variable when try to format the job {job_name}: {str(validate_e)}')

    workflow.start_at = int(pp_datetime.now().timestamp())
    workflow.state = WorkflowState.RUNNING
    # Schedules all jobs to make them executable
    for job in workflow.owned_jobs:
        schedule_job(session, job)
    # A workaround to speed up the workflow execution: manually trigger the start of jobs
    for job in workflow.owned_jobs:
        start_job_if_ready(session, job)


def _notify_if_finished(session: Session, workflow: Workflow):
    if workflow.state not in [WorkflowState.FAILED, WorkflowState.STOPPED, WorkflowState.COMPLETED]:
        return
    creator = UserService(session).get_user_by_username(workflow.creator)
    email_address = None
    if creator:
        email_address = creator.email
    send_email(email_address,
               NotificationTemplateName.WORKFLOW_COMPLETE,
               name=workflow.name,
               state=workflow.state.name,
               link=get_link(f'/v2/workflow-center/workflows/{workflow.id}'))


def stop_workflow_locally(session: Session, workflow: Workflow):
    """Stops the workflow locally, it does not affect other participants."""
    if not workflow.can_transit_to(WorkflowState.STOPPED):
        raise RuntimeError(f'invalid workflow state {workflow.state} when try to stop')

    workflow.stop_at = int(pp_datetime.now().timestamp())
    if workflow.is_failed():
        workflow.state = WorkflowState.FAILED
    elif workflow.is_finished():
        workflow.state = WorkflowState.COMPLETED
    else:
        workflow.state = WorkflowState.STOPPED
    try:
        for job in workflow.owned_jobs:
            stop_job(session, job)
        _notify_if_finished(session, workflow)
    except RuntimeError as e:
        logging.error(f'Failed to stop workflow {workflow.id}: {str(e)}')
        raise


def invalidate_workflow_locally(session: Session, workflow: Workflow):
    """Invalidates workflow locally and stops related jobs."""
    logging.info(f'Invalidating workflow {workflow.id}')
    # Stops the related cron jobs
    update_cronjob_config(workflow.id, None, session)
    # Marks the workflow's state
    workflow.state = WorkflowState.INVALID
    workflow.target_state = WorkflowState.INVALID
    workflow.transaction_state = TransactionState.READY
    # Stops owned jobs
    for job in workflow.owned_jobs:
        try:
            stop_job(session, job)
        except Exception as e:  # pylint: disable=broad-except
            logging.warning('Error while stopping job %s during invalidation: %s', job.name, repr(e))

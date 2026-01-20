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
import traceback
from typing import Tuple

from sqlalchemy.orm import load_only, joinedload

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.proto.composer_pb2 import RunnerOutput, WorkflowSchedulerOutput
from fedlearner_webconsole.utils import const
from fedlearner_webconsole.workflow.service import WorkflowService
from fedlearner_webconsole.workflow.workflow_job_controller import start_workflow, stop_workflow
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from fedlearner_webconsole.composer.interface import IRunnerV2


class ScheduleWorkflowRunner(IRunnerV2):

    def auto_run_workflows(self) -> WorkflowSchedulerOutput:
        with db.session_scope() as session:
            # Workflows (with system preset template) whose state is ready will auto run.
            query = session.query(Workflow.id).join(Workflow.template).filter(
                Workflow.state == WorkflowState.READY, WorkflowTemplate.name.in_(const.SYS_PRESET_TEMPLATE))
            workflow_ids = [result[0] for result in query.all()]
        output = WorkflowSchedulerOutput()
        for workflow_id in workflow_ids:
            execution = output.executions.add()
            execution.id = workflow_id
            try:
                logging.info(f'[WorkflowScheduler] auto start workflow {workflow_id}')
                start_workflow(workflow_id)
            except Exception as e:  # pylint: disable=broad-except
                error = str(e)
                logging.warning(f'[WorkflowScheduler] auto start workflow {workflow_id} with error {error}')
                execution.error_message = error
        return output

    def auto_stop_workflows(self) -> WorkflowSchedulerOutput:
        with db.session_scope() as session:
            # only query fields necessary for is_finished and is_failed.
            q = session.query(Workflow).options(
                load_only(Workflow.id, Workflow.name, Workflow.target_state, Workflow.state),
                joinedload(Workflow.owned_jobs).load_only(Job.state,
                                                          Job.is_disabled)).filter_by(state=WorkflowState.RUNNING)
            workflow_ids = [w.id for w in q.all() if WorkflowService(session).should_auto_stop(w)]
        output = WorkflowSchedulerOutput()
        for workflow_id in workflow_ids:
            execution = output.executions.add()
            execution.id = workflow_id
            try:
                stop_workflow(workflow_id)
            except Exception as e:  # pylint: disable=broad-except
                error = f'Error while auto-stop workflow {workflow_id}:\n{traceback.format_exc()}'
                logging.warning(error)
                execution.error_message = error
        return output

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        output = RunnerOutput()
        try:
            output.workflow_scheduler_output.MergeFrom(self.auto_stop_workflows())
        except Exception as e:  # pylint: disable=broad-except
            error_message = str(e)
            output.error_message = error_message
            logging.warning(f'[SchedulerWorkflowRunner] auto stop workflow with error {error_message}')

        try:
            # TODO(xiangyuxuan.prs): remove in future when model module don't need config workflow.
            output.workflow_scheduler_output.MergeFrom(self.auto_run_workflows())
        except Exception as e:  # pylint: disable=broad-except
            error_message = str(e)
            output.error_message = f'{output.error_message} {error_message}'
            logging.warning(f'[SchedulerWorkflowRunner] auto run workflow with error {error_message}')

        if output.error_message:
            return RunnerStatus.FAILED, output
        return RunnerStatus.DONE, output

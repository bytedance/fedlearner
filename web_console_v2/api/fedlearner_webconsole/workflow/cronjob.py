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

# coding: utf-8
import logging
from typing import Tuple

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.interface import IRunnerV2
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.composer_pb2 import RunnerOutput, WorkflowCronJobOutput
from fedlearner_webconsole.workflow.models import Workflow, WorkflowExternalState
from fedlearner_webconsole.workflow.workflow_job_controller import start_workflow


class WorkflowCronJob(IRunnerV2):
    """Starts workflow periodically.
    """

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        output = WorkflowCronJobOutput()
        with db.session_scope() as session:
            workflow_id = context.input.workflow_cron_job_input.workflow_id
            workflow: Workflow = session.query(Workflow).get(workflow_id)
            state = workflow.get_state_for_frontend()
            logging.info(f'[WorkflowCronJob] Try to start workflow {workflow_id}, state: {state.name}')
            if state in (WorkflowExternalState.READY_TO_RUN, WorkflowExternalState.COMPLETED,
                         WorkflowExternalState.FAILED, WorkflowExternalState.STOPPED):
                start_workflow(workflow_id)
                output.message = 'Restarted workflow'
            else:
                output.message = f'Skip starting workflow, state is {state.name}'
        return RunnerStatus.DONE, RunnerOutput(workflow_cron_job_output=output)

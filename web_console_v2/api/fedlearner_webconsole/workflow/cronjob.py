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

from typing import Tuple
from fedlearner_webconsole.composer.interface import IItem, IRunner, ItemType
from fedlearner_webconsole.composer.models import Context, RunnerStatus
from fedlearner_webconsole.db import get_session
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState


class WorkflowCronJobItem(IItem):
    def __init__(self, task_id: int):
        self.id = task_id

    def type(self) -> ItemType:
        return ItemType.WORKFLOW_CRON_JOB

    def get_id(self) -> int:
        return self.id

    def __eq__(self, obj: IItem):
        return self.id == obj.id and self.type() == obj.type()


class WorkflowCronJob(IRunner):
    """ start workflow every intervals
    """
    def __init__(self, task_id: int):
        self._workflow_id = task_id
        self._msg = None

    def start(self, context: Context):
        with get_session(context.db_engine) as session:
            workflow: Workflow = session.query(Workflow).filter_by(
                id=self._workflow_id).one()
            if workflow.state in (WorkflowState.STOPPED, WorkflowState.READY):
                workflow.update_target_state(
                    target_state=WorkflowState.RUNNING)
                session.commit()
                self._msg = f'restarted workflow[{self._workflow_id}]'
            elif workflow.state == WorkflowState.RUNNING:
                self._msg = f'skip restarting workflow[{self._workflow_id}]'
            elif workflow.state == WorkflowState.INVALID:
                self._msg = f'current workflow[{self._workflow_id}] is invalid'

    def stop(self, context: Context):
        del self, context  # unused by stop fn

    def result(self, context: Context) -> Tuple[RunnerStatus, dict]:
        del context  # unused by result

        output = {'msg': self._msg}
        return RunnerStatus.DONE, output

    def timeout(self, context: Context):
        del self, context  # unused by timeout

        return -1

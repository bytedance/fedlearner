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
import logging
from typing import Tuple

from sqlalchemy.orm import Session

from fedlearner_webconsole.workflow.service import WorkflowService
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData
from fedlearner_webconsole.two_pc.resource_manager import ResourceManager
from fedlearner_webconsole.workflow.workflow_controller import start_workflow_locally, stop_workflow_locally


class WorkflowStateController(ResourceManager):

    def __init__(self, session: Session, tid: str, data: TransactionData):
        super().__init__(tid, data)
        assert data.transit_workflow_state_data is not None
        self._data = data.transit_workflow_state_data
        self._session = session
        self._state_convert_map = {
            WorkflowState.RUNNING: lambda workflow: start_workflow_locally(self._session, workflow),
            WorkflowState.STOPPED: lambda workflow: stop_workflow_locally(self._session, workflow),
        }

    def prepare(self) -> Tuple[bool, str]:
        workflow = self._session.query(Workflow).filter_by(uuid=self._data.workflow_uuid).first()
        if workflow is None:
            message = f'failed to find workflow, uuid is {self._data.workflow_uuid}'
            logging.warning(f'[workflow state 2pc] prepare: {message}, uuid: {self._data.workflow_uuid}')
            return False, message

        if WorkflowState[self._data.target_state] not in self._state_convert_map:
            message = f'illegal target state {self._data.target_state}, uuid: {self._data.workflow_uuid}'
            logging.warning(f'[workflow state 2pc] prepare: {message}')
            return False, message
        if not workflow.can_transit_to(WorkflowState[self._data.target_state]):
            message = f'change worflow state from {workflow.state.name} to {self._data.target_state} is forbidden, \
                uuid: {self._data.workflow_uuid}'

            logging.warning(f'[workflow state 2pc] prepare: {message}')
            return False, message

        if WorkflowState[self._data.target_state] == WorkflowState.STOPPED:
            return True, ''

        is_valid, info = WorkflowService(self._session).validate_workflow(workflow)
        if not is_valid:
            job_name, validate_e = info
            message = f'Invalid variable when try to format the job ' f'{job_name}:{str(validate_e)}, \
                uuid: {self._data.workflow_uuid}'

            logging.warning(f'[workflow state 2pc] prepare: {message}')
            return False, message
        return True, ''

    def commit(self) -> Tuple[bool, str]:
        workflow = self._session.query(Workflow).filter_by(uuid=self._data.workflow_uuid).first()
        if workflow.is_invalid():
            message = 'workflow is already invalidated by participant'
            logging.error(f'[workflow state 2pc] commit: {message}, uuid: {self._data.workflow_uuid}')
            raise ValueError(message)
        try:
            self._state_convert_map[WorkflowState[self._data.target_state]](workflow)
        except RuntimeError as e:
            logging.error(f'[workflow state 2pc] commit: {e}, uuid: {self._data.workflow_uuid}')
            raise
        return True, ''

    def abort(self) -> Tuple[bool, str]:
        logging.info('[workflow state 2pc] abort')
        return True, ''

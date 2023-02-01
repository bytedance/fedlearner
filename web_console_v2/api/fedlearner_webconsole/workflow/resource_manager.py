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
from sqlalchemy.orm import Session
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState, \
    VALID_TRANSACTION_TRANSITIONS, \
    IGNORED_TRANSACTION_TRANSITIONS, TransactionState
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.workflow.service import WorkflowService


def _merge_variables(base, new, access_mode):
    new_dict = {i.name: i for i in new}
    for var in base:
        if var.access_mode in access_mode and var.name in new_dict:
            var.typed_value.CopyFrom(new_dict[var.name].typed_value)
            # TODO(xiangyuxuan.prs): remove when value is deprecated in Variable
            var.value = new_dict[var.name].value


# TODO(hangweiqiang): move it to utils
def merge_workflow_config(base, new, access_mode):
    _merge_variables(base.variables, new.variables, access_mode)
    if not new.job_definitions:
        return
    assert len(base.job_definitions) == len(new.job_definitions)
    for base_job, new_job in \
            zip(base.job_definitions, new.job_definitions):
        _merge_variables(base_job.variables, new_job.variables, access_mode)


class ResourceManager:

    def __init__(self, session: Session, workflow: Workflow):
        self._session = session
        self._workflow = workflow

    def update_state(self, asserted_state, target_state, transaction_state):
        if self._workflow.is_invalid():
            return self._workflow.transaction_state

        assert asserted_state is None or \
               self._workflow.state == asserted_state, \
            'Cannot change current state directly'

        if transaction_state != self._workflow.transaction_state:
            if (self._workflow.transaction_state, transaction_state) in \
                    IGNORED_TRANSACTION_TRANSITIONS:
                return self._workflow.transaction_state
            assert (self._workflow.transaction_state, transaction_state) in \
                   VALID_TRANSACTION_TRANSITIONS, \
                f'Invalid transaction transition from {self._workflow.transaction_state} to {transaction_state}'
            self._workflow.transaction_state = transaction_state

        # coordinator prepare & rollback
        if self._workflow.transaction_state == \
                TransactionState.COORDINATOR_PREPARE:
            self.prepare(target_state)
        if self._workflow.transaction_state == \
                TransactionState.COORDINATOR_ABORTING:
            self.rollback()

        # participant prepare & rollback & commit
        if self._workflow.transaction_state == \
                TransactionState.PARTICIPANT_PREPARE:
            self.prepare(target_state)
        if self._workflow.transaction_state == \
                TransactionState.PARTICIPANT_ABORTING:
            self.rollback()
            self._workflow.transaction_state = TransactionState.ABORTED
        if self._workflow.transaction_state == \
                TransactionState.PARTICIPANT_COMMITTING:
            self.commit()

        return self._workflow.transaction_state

    def prepare(self, target_state):
        assert self._workflow.transaction_state in [
            TransactionState.COORDINATOR_PREPARE,
            TransactionState.PARTICIPANT_PREPARE], \
            'Workflow not in prepare state'

        # TODO(tjulinfan): remove this
        if target_state is None:
            # No action
            return

        # Validation
        try:
            self._workflow.update_target_state(target_state)
        except ValueError as e:
            logging.warning('Error during update target state in prepare: %s', str(e))
            self._workflow.transaction_state = TransactionState.ABORTED
            return

        success = True
        if self._workflow.target_state == WorkflowState.READY:
            success = self._prepare_for_ready()

        if success:
            if self._workflow.transaction_state == \
                    TransactionState.COORDINATOR_PREPARE:
                self._workflow.transaction_state = \
                    TransactionState.COORDINATOR_COMMITTABLE
            else:
                self._workflow.transaction_state = \
                    TransactionState.PARTICIPANT_COMMITTABLE

    def rollback(self):
        self._workflow.target_state = WorkflowState.INVALID

    # TODO: separate this method to another module
    def commit(self):
        assert self._workflow.transaction_state in [
            TransactionState.COORDINATOR_COMMITTING,
            TransactionState.PARTICIPANT_COMMITTING], \
            'Workflow not in prepare state'

        if self._workflow.target_state == WorkflowState.READY:
            self._workflow.fork_proposal_config = None

        self._workflow.state = self._workflow.target_state
        self._workflow.target_state = WorkflowState.INVALID
        self._workflow.transaction_state = TransactionState.READY

    def _prepare_for_ready(self):
        # This is a hack, if config is not set then
        # no action needed
        if self._workflow.transaction_state == \
                TransactionState.COORDINATOR_PREPARE:
            # TODO(tjulinfan): validate if the config is legal or not
            return bool(self._workflow.config)

        if self._workflow.forked_from:
            peer_workflow = WorkflowService(self._session).get_peer_workflow(self._workflow)
            base_workflow = self._session.query(Workflow).get(self._workflow.forked_from)
            if base_workflow is None or not base_workflow.forkable:
                return False
            self._workflow.forked_from = base_workflow.id
            self._workflow.forkable = base_workflow.forkable
            self._workflow.set_create_job_flags(peer_workflow.peer_create_job_flags)
            self._workflow.set_peer_create_job_flags(peer_workflow.create_job_flags)
            config = base_workflow.get_config()
            merge_workflow_config(config, peer_workflow.fork_proposal_config, [common_pb2.Variable.PEER_WRITABLE])
            WorkflowService(self._session).update_config(self._workflow, config)
            logging.error(base_workflow.to_dict())
            self._workflow.template_id = base_workflow.template_id
            self._workflow.editor_info = base_workflow.editor_info
            # TODO: set forked workflow in grpc server
            WorkflowService(self._session).setup_jobs(self._workflow)
            return True

        return bool(self._workflow.config)

    def log_states(self):
        workflow = self._workflow
        logging.debug('workflow %d updated to state=%s, target_state=%s, '
                      'transaction_state=%s', workflow.id, workflow.state.name, workflow.target_state.name,
                      workflow.transaction_state.name)

    def update_local_state(self):
        if self._workflow.target_state == WorkflowState.INVALID:
            return
        self._workflow.state = self._workflow.target_state
        self._workflow.target_state = WorkflowState.INVALID

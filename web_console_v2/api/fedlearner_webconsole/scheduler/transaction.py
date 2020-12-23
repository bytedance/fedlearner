# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
# pylint: disable=broad-except

from fedlearner_webconsole.db import db
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.workflow.models import (
    Workflow, WorkflowState, TransactionState
)
from fedlearner_webconsole.proto import common_pb2

class TransactionManager(object):
    VALID_TRANSITIONS = [
        (WorkflowState.NEW, WorkflowState.READY),
        (WorkflowState.READY, WorkflowState.RUNNING),
        (WorkflowState.RUNNING, WorkflowState.STOPPED),
        (WorkflowState.STOPPED, WorkflowState.READY)
    ]

    VALID_TRANSACTION_TRANSITIONS = [
        (TransactionState.ABORTED, TransactionState.READY),
        (TransactionState.READY, TransactionState.PARTICIPANT_ABORTING),

        (TransactionState.READY, TransactionState.COORDINATOR_PREPARE),
        # (TransactionState.COORDINATOR_PREPARE,
        #  TransactionState.COORDINATOR_COMMITTABLE),
        (TransactionState.COORDINATOR_COMMITTABLE,
         TransactionState.COORDINATOR_COMMITTING),
        # (TransactionState.COORDINATOR_PREPARE,
        #  TransactionState.COORDINATOR_ABORTING),
        (TransactionState.COORDINATOR_COMMITTABLE,
         TransactionState.COORDINATOR_ABORTING),
        (TransactionState.COORDINATOR_ABORTING,
         TransactionState.ABORTED),

        (TransactionState.READY, TransactionState.PARTICIPANT_PREPARE),
        # (TransactionState.PARTICIPANT_PREPARE,
        #  TransactionState.PARTICIPANT_COMMITTABLE),
        (TransactionState.PARTICIPANT_COMMITTABLE,
         TransactionState.PARTICIPANT_COMMITTING),
        # (TransactionState.PARTICIPANT_PREPARE,
        #  TransactionState.PARTICIPANT_ABORTING),
        (TransactionState.PARTICIPANT_COMMITTABLE,
         TransactionState.PARTICIPANT_ABORTING),
        # (TransactionState.PARTICIPANT_ABORTING,
        #  TransactionState.ABORTED),
    ]

    def __init__(self, workflow_id):
        self._workflow_id = workflow_id
        self._workflow = Workflow.query.get(workflow_id)
        self._project = Project.query.get(self._workflow.project_id)
        self._sess = db.create_session(None)

    @property
    def workflow(self):
        return self._workflow

    @property
    def project(self):
        return self._project

    def update_state(self, state, target_state, transaction_state):
        if state is not None and self._workflow.state != state:
            return self._workflow.transaction_state

        if target_state and self._workflow.target_state != target_state:
            if self._workflow.target_state == WorkflowState.INVALID:
                self._workflow.target_state = target_state
            else:
                return self._workflow.transaction_state

        changed = False
        if transaction_state is not None:
            if (self._workflow.transaction_state, transaction_state) in \
                    TransactionManager.VALID_TRANSACTION_TRANSITIONS:
                self._workflow.transaction_state = transaction_state
                changed = True
        
        if not changed:
            self._reload()
            return self._workflow.transaction_state

        # coordinator prepare & rollback
        if changed and self._workflow.transaction_state == \
                TransactionState.COORDINATOR_PREPARE:
            try:
                if self._prepare():
                    self._workflow.transaction_state = \
                        TransactionState.COORDINATOR_COMMITTABLE
            except Exception as e:
                self._workflow.transaction_state = \
                    TransactionState.COORDINATOR_ABORTING

        if changed and self._workflow.transaction_state == \
                TransactionState.COORDINATOR_ABORTING:
            try:
                self._rollback()
            except Exception as e:
                pass

        # participant prepare & rollback & commit
        if changed and self._workflow.transaction_state == \
                TransactionState.PARTICIPANT_PREPARE:
            try:
                if self._prepare():
                    self._workflow.transaction_state = \
                        TransactionState.PARTICIPANT_COMMITTABLE
            except Exception as e:
                self._workflow.transaction_state = \
                    TransactionState.PARTICIPANT_ABORTING

        if self._workflow.transaction_state == \
                TransactionState.PARTICIPANT_ABORTING:
            try:
                self._rollback()
            except Exception as e:
                pass
            self._workflow.target_state = WorkflowState.INVALID
            self._workflow.transaction_state = \
                TransactionState.ABORTED

        if self._workflow.transaction_state == \
                TransactionState.PARTICIPANT_COMMITTING:
            self.commit()

        self._reload()
        return self._workflow.transaction_state

    def commit(self):
        if self._workflow.target_state == WorkflowState.STOPPED:
            # TODO: delete jobs from k8s
            pass
        elif self._workflow.target_state == WorkflowState.READY:
            # TODO: create workflow jobs in database according to config
            pass

        self._workflow.state = self._workflow.target_state
        self._workflow.target_state = WorkflowState.INVALID
        self._workflow.transaction_state = TransactionState.READY
        self._reload()

    def process(self):
        # reload workflow and resolve -ing states
        self.update_state(
            self._workflow.state, self._workflow.target_state,
            self._workflow.transaction_state)

        if not self._recover_from_abort():
            return

        if self._workflow.target_state == WorkflowState.INVALID:
            return

        if self._workflow.state == WorkflowState.INVALID:
            raise RuntimeError(
                "Cannot process invalid workflow %s"%self._workflow.name)

        assert (self._workflow.state, self._workflow.target_state) \
            in TransactionManager.VALID_TRANSITIONS

        if self._workflow.transaction_state == TransactionState.READY:
            # prepare self as coordinator
            self.update_state(
                None, None, TransactionState.COORDINATOR_PREPARE)

        if self._workflow.transaction_state == \
                TransactionState.COORDINATOR_COMMITTABLE:
            # prepare self succeeded. Tell participants to prepare
            states = self._broadcast_state(
                self._workflow.state, self._workflow.target_state,
                TransactionState.PARTICIPANT_PREPARE)
            committable = True
            for state in states:
                if state != TransactionState.PARTICIPANT_COMMITTABLE:
                    committable = False
                if state == TransactionState.ABORTED:
                    # abort as coordinator if some participants aborted
                    self.update_state(
                        None, None, TransactionState.COORDINATOR_ABORTING)
                    break
            # commit as coordinator if participants all committable
            if committable:
                self.update_state(
                    None, None, TransactionState.COORDINATOR_COMMITTING)

        if self._workflow.transaction_state == \
                TransactionState.COORDINATOR_COMMITTING:
            # committing as coordinator. tell participants to commit
            if self._broadcast_state_and_check(
                    self._workflow.state, self._workflow.target_state,
                    TransactionState.PARTICIPANT_COMMITTING,
                    TransactionState.READY):
                # all participants committed. finish.
                self.commit()

        self._recover_from_abort()

    def _reload(self):
        self._sess.commit()
        self._workflow = self._sess.query(Workflow).get(self._workflow_id)

    # returns bool: whether is prepare successed immediately and committable
    def _prepare(self):
        if self._workflow.target_state == WorkflowState.READY:
            return False
        if self._workflow.target_state == WorkflowState.RUNNING:
            return True
        if self._workflow.target_state == WorkflowState.STOPPED:
            return True
        raise RuntimeError(
            "Invalid target_state %s"%self._workflow.target_state)

    def _rollback(self):
        pass

    def _broadcast_state(
            self, state, target_state, transaction_state):
        project_config = self._project.get_config()
        states = []
        for receiver_name in project_config.participants:
            client = RpcClient(None, receiver_name, self._project.get_config())
            resp = client.update_workflow_transaction_state(
                state, target_state, transaction_state)
            if resp.status.code == common_pb2.STATUS_SUCCESS:
                states.append(TransactionState(resp.state))
            else:
                states.append(None)
        return states

    def _broadcast_state_and_check(self,
            state, target_state, transaction_state, target_transaction_state):
        states = self._broadcast_state(state, target_state, transaction_state)
        for i in states:
            if i != target_transaction_state:
                return False
        return True

    def _recover_from_abort(self):
        if self._workflow.transaction_state == \
                TransactionState.COORDINATOR_ABORTING:
            if not self._broadcast_state_and_check(
                    self._workflow.state, WorkflowState.INVALID,
                    TransactionState.PARTICIPANT_ABORTING,
                    TransactionState.ABORTED):
                return False
            self.update_state(
                None, WorkflowState.INVALID, TransactionState.ABORTED)

        if self._workflow.transaction_state != TransactionState.ABORTED:
            return True

        assert self._workflow.target_state == WorkflowState.INVALID

        if not self._broadcast_state_and_check(
                self._workflow.state, WorkflowState.INVALID,
                TransactionState.READY, TransactionState.READY):
            return False
        self.update_state(None, None, TransactionState.READY)
        return True

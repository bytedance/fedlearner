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

from fedlearner_webconsole.db import db
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.workflow.models import (
    Workflow, WorkflowState, TransactionState, VALID_TRANSITIONS
)
from fedlearner_webconsole.proto import common_pb2

class TransactionManager(object):
    def __init__(self, workflow_id):
        self._workflow_id = workflow_id
        self._workflow = Workflow.query.get(workflow_id)
        assert self._workflow is not None
        self._project = self._workflow.project
        assert self._project is not None

    @property
    def workflow(self):
        return self._workflow

    @property
    def project(self):
        return self._project

    def process(self):
        # reload workflow and resolve -ing states
        self._workflow.update_state(
            self._workflow.state, self._workflow.target_state,
            self._workflow.transaction_state)
        self._reload()

        if not self._recover_from_abort():
            return self._workflow

        if self._workflow.target_state == WorkflowState.INVALID:
            return self._workflow

        if self._workflow.state == WorkflowState.INVALID:
            raise RuntimeError(
                "Cannot process invalid workflow %s"%self._workflow.name)

        assert (self._workflow.state, self._workflow.target_state) \
            in VALID_TRANSITIONS

        if self._workflow.transaction_state == TransactionState.READY:
            # prepare self as coordinator
            self._workflow.update_state(
                self._workflow.state,
                self._workflow.target_state,
                TransactionState.COORDINATOR_PREPARE)
            self._reload()

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
                    self._workflow.update_state(
                        None, None, TransactionState.COORDINATOR_ABORTING)
                    self._reload()
                    break
            # commit as coordinator if participants all committable
            if committable:
                self._workflow.update_state(
                    None, None, TransactionState.COORDINATOR_COMMITTING)
                self._reload()

        if self._workflow.transaction_state == \
                TransactionState.COORDINATOR_COMMITTING:
            # committing as coordinator. tell participants to commit
            if self._broadcast_state_and_check(
                    self._workflow.state, self._workflow.target_state,
                    TransactionState.PARTICIPANT_COMMITTING,
                    TransactionState.READY):
                # all participants committed. finish.
                self._workflow.commit()
                self._reload()

        self._recover_from_abort()
        return self._workflow

    def _reload(self):
        db.session.commit()
        db.session.refresh(self._workflow)

    def _broadcast_state(
            self, state, target_state, transaction_state):
        project_config = self._project.get_config()
        states = []
        for party in project_config.participants:
            client = RpcClient(project_config, party)
            forked_from_uuid = Workflow.query.filter_by(
                id=self._workflow.forked_from
            ).first().uuid if self._workflow.forked_from else None
            resp = client.update_workflow_state(
                self._workflow.name, state, target_state, transaction_state,
                self._workflow.uuid,
                forked_from_uuid)
            if resp.status.code == common_pb2.STATUS_SUCCESS:
                if resp.state == WorkflowState.INVALID:
                    self._workflow.invalidate()
                    self._reload()
                    raise RuntimeError("Peer workflow invalidated. Abort.")
                states.append(TransactionState(resp.transaction_state))
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
            self._workflow.update_state(
                None, WorkflowState.INVALID, TransactionState.ABORTED)
            self._reload()

        if self._workflow.transaction_state != TransactionState.ABORTED:
            return True

        assert self._workflow.target_state == WorkflowState.INVALID

        if not self._broadcast_state_and_check(
                self._workflow.state, WorkflowState.INVALID,
                TransactionState.READY, TransactionState.READY):
            return False
        self._workflow.update_state(None, None, TransactionState.READY)
        self._reload()
        return True

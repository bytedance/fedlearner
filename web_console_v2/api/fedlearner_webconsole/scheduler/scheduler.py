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

import os
import threading
import logging

from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.rpc.client import RpcClient


def _check_states_in(states, valid_states):
    if not isinstance(states, list):
        states = [states]
    for state in states:
        if state not in valid_states:
            return False
    return True


class Scheduler(object):
    def __init__(self):
        self._condition = threading.Condition(threading.RLock())
        self._running = False
        self._terminate = False
        self._thread = None
        self._pending = []

    def start(self, force=False):
        if self._running:
            if not force:
                raise RuntimeError("Scheduler is already started")
            self.stop()

        with self._condition:
            self._running = True
            self._terminate = False
            self._thread = threading.Thread(target=self._routine)
            self._thread.start()
    
    def stop(self):
        if not self._running:
            return

        with self._condition:
            self._terminate = True
            self._condition.notify_all()
        self._thread.join()
        self._running = False

    def workflow_start_coordinator(self, workflow_id):
        workflow, project = self._get_workflow_and_project(workflow_id)
        assert workflow.state == WorkflowState.CREATED or \
            workflow.state == WorkflowState.RUNNING_COORDINATOR_PREPARE or \
            workflow.state == WorkflowState.RUNNING_COORDINATOR_COMMITTABLE,
                "Cannot start workflow %s: Wrong state %d"%(
                    workflow.name, workflow.state)

        # startup self
        workflow.update_state(
            workflow.state, WorkflowState.RUNNING_COORDINATOR_COMMITTABLE)
        db.session.commit()

        # prepare
        states = self._send_workflow_state(
            project, workflow, WorkflowState.RUNNING_PARTICIPANT_PREPARE)

        if _check_states_in(
                states, [WorkflowState.RUNNING_PARTICIPANT_COMMITTABLE]):
            # ready to commit
            self._send_workflow_state(
                project, workflow, WorkflowState.RUNNING)
            workflow.update_state(
                workflow.state, WorkflowState.RUNNING)
            db.session.commit()
            return workflow.state
        
        if not _check_states_in(
                states, [None, WorkflowState.RUNNING_PARTICIPANT_PREPARE,
                         WorkflowState.RUNNING_PARTICIPANT_COMMITTABLE]):
            workflow.update_state(
                workflow.state, WorkflowState.RUNNING_ABORT)
            db.session.commit()
            # clear workflow and jobs

            workflow.update_state(
                workflow.state, WorkflowState.CREATED)
            db.session.commit()
            return workflow.state

        return workflow.state

    def workflow_update_state(self, workflow_id, new_state):
        workflow, project = self._get_workflow_and_project(workflow_id)
        if new_state == WorkflowState.RUNNING_PARTICIPANT_PREPARE:
            if _check_states_in(
                    workflow.state,
                    [WorkflowState.CREATED,
                     WorkflowState.RUNNING_PARTICIPANT_PREPARE,
                     WorkflowState.RUNNING_PARTICIPANT_COMMITTABLE]):
                workflow.update_state(
                    workflow.state,
                    WorkflowState.RUNNING_PARTICIPANT_COMMITTABLE)
                db.session.commit()
        
        if new_state == WorkflowState.RUNNING:
            if workflow.state == WorkflowState.RUNNING_PARTICIPANT_COMMITTABLE
                workflow.update_state(
                    workflow.state, WorkflowState.RUNNING)
                db.session.commit()
        
        return workflow.state

    def _routine(self):
        interval = os.environ.get(
            "FEDLEARNER_WEBCONSOLE_POLLING_INTERVAL", 300)

        while True:
            with self._condition:
                timeout = self._condition.wait(interval)
                if self._terminate:
                    return
                if timeout:
                    self._pending.clear()
                    self._resolve_pending()
                else:
                    self._poll()

    def _resolve_pending(self):
        pass

    def _poll(self):
        workflow_ids = db.session.query.with_entities(Workflow.id)
        for workflow_id in workflow_ids:
            try:
                self._schedule_workflow(workflow_id)
            except Exception as e:
                logging.warning(
                    "Error while scheduling workflow %d: %s",
                    workflow_id, e)
    
    
    def _schedule_workflow(self, workflow_id):
        if workflow.state == WorkflowState.RUNNING_COORDINATOR_PREPARE:


    def _send_workflow_state(self, project, state):
        project_config = project.get_config()
        states = []
        for receiver_name in project_config.participants:
            client = RpcClient(project, receiver_name)
            resp = client.update_workflow_state(state)
            if resp.status.code = common_pb2.STATUS_SUCCESS:
                states.append(resp.state)
            else:
                states.append(None)
        return states

    def _get_workflow_and_project(self, workflow_id):
        workflow = Workflow.query.filter(id=workflow_id).first()
        assert workflow is not None, \
            "Workflow with id %d not found"%workflow_id
        project = Project.query.filter(id=workflow.project_id).first()
        assert project is not None, \
            "Workflow %s has invalid project id %d"%(
                workflow.name, workflow.project_id)
        return workflow, project
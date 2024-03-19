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
# pylint: disable=broad-except
import threading
import logging
import traceback
from queue import Queue, Empty
from envs import Envs
from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.scheduler.transaction import TransactionManager


class Scheduler(object):

    def __init__(self):
        self._condition = threading.Condition(threading.RLock())
        self._running = False
        self._terminate = False
        self._thread = None
        self.workflow_queue = Queue()

    def start(self, force=False):
        if self._running:
            if not force:
                raise RuntimeError('Scheduler is already started')
            self.stop()

        with self._condition:
            self._running = True
            self._terminate = False
            self._thread = threading.Thread(target=self._routine)
            self._thread.daemon = True
            self._thread.start()
            logging.info('Scheduler started')

    def stop(self):
        if not self._running:
            return

        with self._condition:
            self._terminate = True
            # Interrupt the block of workflow_queue.get to stop immediately.
            self.workflow_queue.put(None)
            print('stopping')
        self._thread.join()
        self._running = False
        logging.info('Scheduler stopped')

    def wakeup(self, workflow_id=None):
        self.workflow_queue.put(workflow_id)

    def _routine(self):
        interval = float(Envs.SCHEDULER_POLLING_INTERVAL)

        while True:
            try:
                try:
                    pending_workflow = self.workflow_queue.get(timeout=interval)
                except Empty:
                    pending_workflow = None
                with self._condition:
                    if self._terminate:
                        return
                if pending_workflow:
                    self._poll_workflows([pending_workflow])

                with db.session_scope() as session:
                    workflows = session.query(Workflow.id).filter(Workflow.target_state != WorkflowState.INVALID).all()
                self._poll_workflows([wid for wid, in workflows])
            # make the scheduler routine run forever.
            except Exception as e:
                logging.error(f'Scheduler routine wrong: {str(e)}')

    def _poll_workflows(self, workflow_ids):
        logging.info(f'Scheduler polling {len(workflow_ids)} workflows...')
        for workflow_id in workflow_ids:
            try:
                self._schedule_workflow(workflow_id)
            except Exception as e:
                logging.warning('Error while scheduling workflow ' f'{workflow_id}:\n{traceback.format_exc()}')

    def _schedule_workflow(self, workflow_id):
        logging.debug(f'Scheduling workflow {workflow_id}')
        with db.session_scope() as session:
            tm = TransactionManager(workflow_id, session)
            return tm.process()


scheduler = Scheduler()

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
from fedlearner_webconsole.scheduler.transaction import TransactionManager

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
            self._thread.daemon = True
            self._thread.start()

    def stop(self):
        if not self._running:
            return

        with self._condition:
            self._terminate = True
            self._condition.notify_all()
            print('stopping')
        self._thread.join()
        self._running = False

    def _routine(self):
        interval = os.environ.get(
            "FEDLEARNER_WEBCONSOLE_POLLING_INTERVAL", 300)

        while True:
            with self._condition:
                timeout = self._condition.wait(interval)
                print('timeout', timeout)
                if self._terminate:
                    return
                if timeout:
                    workflow_ids = self._pending
                    self._pending.clear()
                else:
                    workflow_ids = db.session.query.with_entities(Workflow.id)
                self._poll(workflow_ids)

    def _poll(self, workflow_ids):
        for workflow_id in workflow_ids:
            try:
                self._schedule_workflow(workflow_id)
            except Exception as e:
                logging.warning(
                    "Error while scheduling workflow %d: %s",
                    workflow_id, e)

    def _schedule_workflow(self, workflow_id):
        tm = TransactionManager(workflow_id)
        tm.process()

        # schedule jobs in workflow

scheduler = Scheduler()

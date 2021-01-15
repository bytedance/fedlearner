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

import os
import threading
import logging
import traceback

from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.models import JobState
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.scheduler.transaction import TransactionManager

class Scheduler(object):
    def __init__(self):
        self._condition = threading.Condition(threading.RLock())
        self._running = False
        self._terminate = False
        self._thread = None
        self._pending = []
        self._app = None

    def start(self, app, force=False):
        if self._running:
            if not force:
                raise RuntimeError("Scheduler is already started")
            self.stop()

        self._app = app

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
            self._condition.notify_all()
            print('stopping')
        self._thread.join()
        self._running = False
        logging.info('Scheduler stopped')

    def wakeup(self, workflow_id):
        with self._condition:
            self._pending.append(workflow_id)
            self._condition.notify_all()

    def _routine(self):
        self._app.app_context().push()
        interval = int(os.environ.get(
            'FEDLEARNER_WEBCONSOLE_POLLING_INTERVAL', 60))

        while True:
            with self._condition:
                notified = self._condition.wait(interval)
                if self._terminate:
                    return
                if notified:
                    workflow_ids = self._pending
                    self._pending = []
                else:
                    workflow_ids = [
                        wid for wid, in db.session.query(Workflow.id).all()]
                self._poll(workflow_ids)

    def _poll(self, workflow_ids):
        logging.info('Scheduler polling %d workflows...', len(workflow_ids))
        for workflow_id in workflow_ids:
            try:
                self._schedule_workflow(workflow_id)
            except Exception as e:
                logging.warning(
                    "Error while scheduling workflow %d:\n%s",
                    workflow_id, traceback.format_exc())

    def _schedule_workflow(self, workflow_id):
        logging.debug('Scheduling workflow %d', workflow_id)
        tm = TransactionManager(workflow_id)
        workflow = tm.process()
        # schedule jobs in workflow
        if workflow.state == WorkflowState.RUNNING:
            self._schedule_jobs(workflow)

    def _schedule_jobs(self, workflow):
        jobs = workflow.jobs
        name_to_job = {}
        for job in jobs:
            name_to_job[job.name] = job
        for job in jobs:
            if job.state != JobState.READY:
                continue
            ready_to_run = True
            # TODO: use relationships in db
            dependencies = job.get_config().dependencies
            for dependency in dependencies:
                dep_job_name = f'{workflow.name}-{dependency.source}'
                if dep_job_name not in name_to_job:
                    ready_to_run = False
                    break
                if name_to_job[dep_job_name].get_flapp()\
                    ['status']['appState'] != 'FLStateComplete':
                    ready_to_run = False
                    break
            if ready_to_run:
                job.run()
        db.session.commit()


scheduler = Scheduler()

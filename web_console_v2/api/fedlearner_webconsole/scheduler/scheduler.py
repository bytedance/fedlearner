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
from fedlearner_webconsole.job.yaml_formatter import generate_job_run_yaml
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.import_handler import ImportHandler
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.job.models import Job, JobState, JobDependency
from fedlearner_webconsole.scheduler.transaction import TransactionManager
from fedlearner_webconsole.k8s_client import get_client
from fedlearner_webconsole.utils.k8s_client import CrdKind


class Scheduler(object):
    def __init__(self):
        self._condition = threading.Condition(threading.RLock())
        self._running = False
        self._terminate = False
        self._thread = None
        self._pending_workflows = []
        self._pending_jobs = []
        self._app = None
        self._import_handler = ImportHandler()

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
            self._import_handler.init(app)
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

    def wakeup(self, workflow_ids=None,
                     job_ids=None,
                     data_batch_ids=None):
        with self._condition:
            if workflow_ids:
                if isinstance(workflow_ids, int):
                    workflow_ids = [workflow_ids]
                self._pending_workflows.extend(workflow_ids)
            if job_ids:
                if isinstance(job_ids, int):
                    job_ids = [job_ids]
                self._pending_jobs.extend(job_ids)
            if data_batch_ids:
                self._import_handler.schedule_to_handle(data_batch_ids)
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
                    workflow_ids = self._pending_workflows
                    self._pending_workflows = []
                    self._poll_workflows(workflow_ids)

                    job_ids = self._pending_jobs
                    self._pending_jobs = []
                    job_ids.extend([
                        jid for jid, in db.session.query(Job.id) \
                            .filter(Job.state == JobState.WAITING) \
                            .filter(Job.workflow_id in workflow_ids)])
                    self._poll_jobs(job_ids)

                    self._import_handler.handle(pull=False)
                    continue

                workflows = db.session.query(Workflow.id).filter(
                    Workflow.target_state != WorkflowState.INVALID).all()
                self._poll_workflows([wid for wid, in workflows])

                jobs = db.session.query(Job.id).filter(
                    Job.state == JobState.WAITING).all()
                self._poll_jobs([jid for jid, in jobs])

                self._import_handler.handle(pull=True)

    def _poll_workflows(self, workflow_ids):
        logging.info('Scheduler polling %d workflows...', len(workflow_ids))
        for workflow_id in workflow_ids:
            try:
                self._schedule_workflow(workflow_id)
            except Exception as e:
                logging.warning(
                    "Error while scheduling workflow %d:\n%s",
                    workflow_id, traceback.format_exc())

    def _poll_jobs(self, job_ids):
        logging.info('Scheduler polling %d jobs...', len(job_ids))
        for job_id in job_ids:
            try:
                self._schedule_job(job_id)
            except Exception as e:
                logging.warning(
                    "Error while scheduling job %d:\n%s",
                    job_id, traceback.format_exc())

    def _schedule_workflow(self, workflow_id):
        logging.debug('Scheduling workflow %d', workflow_id)
        tm = TransactionManager(workflow_id)
        return tm.process()

    def _schedule_job(self, job_id):
        job = Job.query.get(job_id)
        assert job is not None, 'Job %d not found'%job_id
        if job.state != JobState.WAITING:
            return job.state
        deps = JobDependency.query.filter(
            JobDependency.dst_job_id == job.id).all()
        for dep in deps:
            src_job = Job.query.get(dep.src_job_id)
            assert src_job is not None, 'Job %d not found'%dep.src_job_id
            if not src_job.is_complete():
                return job.state

        k8s_client = get_client()
        yaml = generate_job_run_yaml(job)
        try:
            k8s_client.create_or_replace_custom_object(CrdKind.FLAPP, yaml)
        except RuntimeError as e:
            logging.error('Start job %d has Runtime error msg: %s'
                          , job_id, e.args)
            return job.state
        job.start()
        db.session.commit()

        return job.state


scheduler = Scheduler()

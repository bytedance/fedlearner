# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
from fedlearner_webconsole.utils.k8s_client import k8s_client
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.job.models import Job, JobState
from fedlearner_webconsole.scheduler.transaction import TransactionManager
from fedlearner_webconsole.db import get_session
from fedlearner_webconsole.job.service import JobService


class Scheduler(object):
    def __init__(self):
        self._condition = threading.Condition(threading.RLock())
        self._running = False
        self._terminate = False
        self._thread = None
        self._pending_workflows = []
        self._pending_jobs = []
        #TODO: remove app
        self._app = None
        self._db_engine = None
        self._import_handler = ImportHandler()

    def start(self, app, force=False):
        if self._running:
            if not force:
                raise RuntimeError('Scheduler is already started')
            self.stop()

        self._app = app
        with self._app.app_context():
            self._db_engine = db.get_engine()

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

                # TODO(wangsen): use Sqlalchemy insdtead of flask-Sqlalchemy
                # refresh a new session to catch the update of db
                db.session.remove()
                if self._terminate:
                    return
                if notified:
                    workflow_ids = self._pending_workflows
                    self._pending_workflows = []
                    self._poll_workflows(workflow_ids)

                    job_ids = self._pending_jobs
                    self._pending_jobs = []
                    job_ids.extend(_get_waiting_jobs())
                    self._poll_jobs(job_ids)

                    self._import_handler.handle(pull=False)
                    continue

                workflows = db.session.query(Workflow.id).filter(
                    Workflow.target_state != WorkflowState.INVALID).all()
                self._poll_workflows([wid for wid, in workflows])

                self._poll_jobs(_get_waiting_jobs())

                self._import_handler.handle(pull=True)

    def _poll_workflows(self, workflow_ids):
        logging.info(f'Scheduler polling {len(workflow_ids)} workflows...')
        for workflow_id in workflow_ids:
            try:
                self._schedule_workflow(workflow_id)
            except Exception as e:
                logging.warning(
                    'Error while scheduling workflow '
                    f'{workflow_id}:\n{traceback.format_exc()}')

    def _poll_jobs(self, job_ids):
        logging.info(f'Scheduler polling {len(job_ids)} jobs...')
        for job_id in job_ids:
            try:
                self._schedule_job(job_id)
            except Exception as e:
                logging.warning(
                    'Error while scheduling job '
                    f'{job_id}:\n{traceback.format_exc()}')

    def _schedule_workflow(self, workflow_id):
        logging.debug(f'Scheduling workflow {workflow_id}')
        tm = TransactionManager(workflow_id)
        return tm.process()

    def _schedule_job(self, job_id):
        job = Job.query.get(job_id)
        assert job is not None, f'Job {job_id} not found'
        if job.state != JobState.WAITING:
            return job.state

        with get_session(self._db_engine) as session:
            job_service = JobService(session)
            if not job_service.is_ready(job):
                return job.state
            config = job.get_config()
            if config.is_federated:
                if not job_service.is_peer_ready(job):
                    return job.state

        try:
            yaml = generate_job_run_yaml(job)
            k8s_client.create_flapp(yaml)
        except Exception as e:
            logging.error(f'Start job {job_id} has error msg: {e.args}')
            job.error_message = str(e)
            db.session.commit()
            return job.state
        job.error_message = None
        job.start()
        db.session.commit()

        return job.state


def _get_waiting_jobs():
    return [jid for jid, in db.session.query(
        Job.id).filter(Job.state == JobState.WAITING)]


scheduler = Scheduler()

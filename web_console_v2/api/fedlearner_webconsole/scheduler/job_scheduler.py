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
import threading
import logging
from fedlearner_webconsole.job.models import Job, JobState
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.adapter import ProjectK8sAdapter
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDependency
from fedlearner_webconsole.k8s_client import get_client

class JobScheduler(object):
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
                raise RuntimeError(
                    "Job_Scheduler is already started")
            self.stop()

        self._app = app
        with self._condition:
            self._running = True
            self._terminate = False
            self._thread = threading.Thread(target=self._routine)
            self._thread.daemon = True
            self._thread.start()
            logging.info('Job_Scheduler started')

    def stop(self):
        if not self._running:
            return

        with self._condition:
            self._terminate = True
            self._condition.notify_all()
            print('stopping')
        self._thread.join()
        self._running = False
        logging.info('Job_Scheduler stopped')

    def wakeup(self, job_ids):
        with self._condition:
            for job_id in job_ids:
                if job_id not in self._pending:
                    self._pending.append(job_id)
            self._condition.notify_all()

    def sleep(self, job_ids):
        with self._condition:
            for job_id in job_ids:
                if job_id in self._pending:
                    self._pending.remove(job_id)

    def _run(self, job):
        if job.state != JobState.READY:
            return
        dependencies = job.get_config().dependencies
        for dependency in dependencies:
            depend = Job.query.filter_by(name=dependency.source).first()
            if depend is None or depend.state != JobState.STARTED:
                return
            if dependency.type == JobDependency.ON_COMPLETE:
                if depend.get_custom_object()['status']['appState'] \
                     != 'FLStateComplete':
                    return
        job.state = JobState.STARTED
        project_adapter = ProjectK8sAdapter(job.project_id)
        k8s_client = get_client()
        # TODO: complete yaml
        k8s_client.create_flapp(project_adapter.
                                get_namespace(), job.yaml)

    def _routine(self):
        self._app.app_context().push()
        # TODO: separate the scheduler to a new process to remove this.
        # time.sleep(10)
        # self._pending = [job.id for job in
        #                  Job.query.filter_by(status=JobState.READY)]
        while True:
            with self._condition:
                self._condition.wait(60)
                if self._terminate:
                    return
                job_ids = self._pending
                for job_id in job_ids:
                    job = Job.query.filter_by(id=job_id).first()
                    if job is not None:
                        self._run(job)
                        db.session.commit()


job_scheduler = JobScheduler()

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

import logging
from sqlalchemy.orm.session import Session
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.job.models import Job, JobDependency, JobState
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.utils.metrics import emit_counter


class JobService:

    def __init__(self, session: Session):
        self._session = session

    def is_ready(self, job: Job) -> bool:
        deps = self._session.query(JobDependency).filter_by(
            dst_job_id=job.id).all()
        for dep in deps:
            src_job = self._session.query(Job).get(dep.src_job_id)
            assert src_job is not None, 'Job {} not found'.format(
                dep.src_job_id)
            if not src_job.state == JobState.COMPLETED:
                return False
        return True

    @staticmethod
    def is_peer_ready(job: Job) -> bool:
        project_config = job.project.get_config()
        for party in project_config.participants:
            client = RpcClient(project_config, party)
            resp = client.check_job_ready(job.name)
            if resp.status.code != common_pb2.STATUS_SUCCESS:
                emit_counter('check_peer_ready_failed', 1)
                return True
            if not resp.is_ready:
                return False
        return True

    def update_running_state(self, job_name):
        job = self._session.query(Job).filter_by(name=job_name).first()
        if job is None:
            emit_counter('[JobService]job_not_found', 1)
            return
        if not job.state == JobState.STARTED:
            emit_counter('[JobService]wrong_job_state', 1)
            return
        if job.is_flapp_complete():
            job.complete()
            logging.debug('[JobService]change job %s state to %s',
                          job.name, JobState(job.state))
        elif job.is_flapp_failed():
            job.fail()
            logging.debug('[JobService]change job %s state to %s',
                          job.name, JobState(job.state))

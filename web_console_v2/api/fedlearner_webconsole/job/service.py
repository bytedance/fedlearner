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
import datetime
import json
import logging
from typing import List

from sqlalchemy.orm.session import Session

from fedlearner_webconsole.proto.job_pb2 import CrdMetaData, PodPb
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition
from fedlearner_webconsole.job.models import Job, JobDependency, \
    JobState
from fedlearner_webconsole.utils.metrics import emit_store
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.pp_yaml import compile_yaml_template
from fedlearner_webconsole.job.utils import DurationState, emit_job_duration_store


def serialize_to_json(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    return str(o)


class JobService:

    def __init__(self, session: Session):
        self._session = session

    def is_ready(self, job: Job) -> bool:
        deps = self._session.query(JobDependency).filter_by(dst_job_id=job.id).all()
        for dep in deps:
            src_job = self._session.query(Job).get(dep.src_job_id)
            assert src_job is not None, f'Job {dep.src_job_id} not found'
            if not src_job.state == JobState.COMPLETED:
                return False
        return True

    def update_running_state(self, job_name: str) -> JobState:
        job = self._session.query(Job).filter_by(name=job_name).first()
        if job is None:
            emit_store('job.service.update_running_state_error',
                       1,
                       tags={
                           'job_name': job_name,
                           'reason': 'job_not_found'
                       })
            return None
        if not job.state == JobState.STARTED:
            emit_store('job.service.update_running_state_error',
                       1,
                       tags={
                           'job_name': job_name,
                           'reason': 'wrong_job_state'
                       })
            return job.state
        if job.get_k8s_app().is_completed:
            self.complete(job)
            logging.debug('[JobService]change job %s state to %s', job.name, JobState(job.state))
        elif job.get_k8s_app().is_failed:
            self.fail(job)
            logging.debug('[JobService]change job %s state to %s', job.name, JobState(job.state))
        return job.state

    @staticmethod
    def get_pods(job: Job, include_private_info=True) -> List[PodPb]:
        crd_obj = job.get_k8s_app()
        if crd_obj:
            return [pod.to_proto(include_private_info) for pod in crd_obj.pods]
        return []

    @staticmethod
    def set_config_and_crd_info(job: Job, proto: JobDefinition):
        job.set_config(proto)
        yaml = {}
        try:
            yaml = compile_yaml_template(job.get_config().yaml_template, post_processors=[], ignore_variables=True)
        except Exception as e:  # pylint: disable=broad-except
            # Don't raise exception because of old templates, default None will use FLApp.
            logging.error(
                f'Failed format yaml for job {job.name} when try to get the kind and api_version. msg: {str(e)}')
        kind = yaml.get('kind', None)
        api_version = yaml.get('apiVersion', None)
        job.crd_kind = kind
        job.set_crd_meta(CrdMetaData(api_version=api_version))

    @staticmethod
    def complete(job: Job):
        assert job.state == JobState.STARTED, 'Job State is not STARTED'
        JobService.set_status_to_snapshot(job)
        job.build_crd_service().delete_app()
        job.state = JobState.COMPLETED
        emit_job_duration_store(duration=job.get_complete_at() - to_timestamp(job.created_at),
                                job_name=job.name,
                                state=DurationState.COMPLETED)

    @staticmethod
    def fail(job: Job):
        assert job.state == JobState.STARTED, 'Job State is not STARTED'
        JobService.set_status_to_snapshot(job)
        job.build_crd_service().delete_app()
        job.state = JobState.FAILED
        job.error_message = job.get_k8s_app().error_message
        emit_job_duration_store(duration=job.get_complete_at() - to_timestamp(job.created_at),
                                job_name=job.name,
                                state=DurationState.FAILURE)

    @staticmethod
    def set_status_to_snapshot(job: Job):
        app = job.build_crd_service().get_k8s_app_cache()
        job.snapshot = json.dumps(app, default=serialize_to_json)

    @staticmethod
    def get_job_yaml(job: Job) -> str:
        # Can't query from k8s api server when job is not started.
        if job.state != JobState.STARTED:
            return job.snapshot or ''
        return json.dumps(job.build_crd_service().get_k8s_app_cache(), default=serialize_to_json)

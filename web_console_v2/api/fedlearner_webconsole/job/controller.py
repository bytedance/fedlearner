# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
from typing import Tuple, Optional

from sqlalchemy.orm import Session

from fedlearner_webconsole.job.models import Job, JobState, JobType
from fedlearner_webconsole.job.service import JobService
from fedlearner_webconsole.job.yaml_formatter import YamlFormatterService
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.utils.metrics import emit_store
from fedlearner_webconsole.utils.pp_datetime import now, to_timestamp
from fedlearner_webconsole.job.utils import DurationState, emit_job_duration_store
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.utils.workflow import build_job_name


def _are_peers_ready(session: Session, project: Project, job_name: str) -> bool:
    service = ParticipantService(session)
    participants = service.get_platform_participants_by_project(project.id)
    for participant in participants:
        client = RpcClient.from_project_and_participant(project.name, project.token, participant.domain_name)
        resp = client.check_job_ready(job_name)
        # Fallback solution: we think peer is ready if rpc fails
        if resp.status.code != common_pb2.STATUS_SUCCESS:
            emit_store('job.controller.check_peer_ready_failed', 1)
            continue
        if not resp.is_ready:
            return False
    return True


def schedule_job(unused_session: Session, job: Job):
    del unused_session
    if job.is_disabled:
        # No action
        return
    # COMPLETED/FAILED Job State can be scheduled since stop action will
    # not change the state of completed or failed job
    assert job.state in [JobState.NEW, JobState.STOPPED, JobState.COMPLETED, JobState.FAILED]
    job.snapshot = None
    # Marks the job to be scheduled
    job.state = JobState.WAITING
    job.error_message = None


def start_job_if_ready(session: Session, job: Job) -> Tuple[bool, Optional[str]]:
    """Schedules a job for execution.

    Returns:
        Job readiness and the related message.
    """
    if job.state != JobState.WAITING:
        return False, f'Invalid job state: {job.id} {job.state}'

    # Checks readiness locally
    if not JobService(session).is_ready(job):
        return False, None
    config = job.get_config()
    if config.is_federated:
        # Checks peers' readiness for federated job
        if not _are_peers_ready(session, job.project, job.name):
            return False, None

    _start_job(session, job)
    return True, job.error_message


def _start_job(session: Session, job: Job):
    """Starts a job locally."""
    try:
        assert job.state == JobState.WAITING, 'Job state should be WAITING'
        # Builds yaml by template and submits it to k8s
        yaml = YamlFormatterService(session).generate_job_run_yaml(job)
        job.build_crd_service().create_app(yaml)
        # Updates job status if submitting successfully
        job.state = JobState.STARTED
    except Exception as e:  # pylint: disable=broad-except
        logging.error(f'Start job {job.id} has error msg: {e.args}')
        job.error_message = str(e)


def stop_job(unused_session: Session, job: Job):
    del unused_session  # Unused for now, this argument is to let invoker commit after this function
    if job.state not in [JobState.WAITING, JobState.STARTED, JobState.COMPLETED, JobState.FAILED]:
        logging.warning('illegal job state, name: %s, state: %s', job.name, job.state)
        return
    # state change:
    # WAITING -> NEW
    # STARTED -> STOPPED
    # COMPLETED/FAILED unchanged
    if job.state == JobState.STARTED:
        JobService.set_status_to_snapshot(job)
        job.build_crd_service().delete_app()
        job.state = JobState.STOPPED
        emit_job_duration_store(to_timestamp(now()) - to_timestamp(job.created_at),
                                job_name=job.name,
                                state=DurationState.STOPPED)
    if job.state == JobState.WAITING:
        # This change to make sure no effect on waiting jobs
        job.state = JobState.NEW


def create_job_without_workflow(session: Session,
                                job_def: JobDefinition,
                                project_id: int,
                                name: Optional[str] = None,
                                uuid: Optional[str] = None) -> Optional[Job]:
    """Create a job without workflow.
    Args:
      session: db session, must be committed after this function return.
      job_def:  JobDefinition. job_def.yaml_template should not use any variables of workflow.
      project_id: int indicate a project.
      name: the unique name of the job overriding the default name {uuid}-{job_def.name}
      uuid: {uuid}-{job_def.name} will be the unique name of the job. When job_def.is_federated is True,
       participants in the project must have a job with the same name.
    Returns:
      Optional[Job]
    """
    if name is None:
        if uuid is None:
            uuid = resource_uuid()
        name = build_job_name(uuid, job_def.name)
    job = session.query(Job).filter_by(name=name).first()
    if job is not None:
        return None
    job = Job(name=name, job_type=JobType(job_def.job_type), workflow_id=0, project_id=project_id, state=JobState.NEW)
    JobService.set_config_and_crd_info(job, job_def)
    session.add(job)
    return job

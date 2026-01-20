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
from typing import Tuple

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.interface import IRunnerV2
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.controller import start_job_if_ready
from fedlearner_webconsole.job.models import Job, JobState
from fedlearner_webconsole.proto.composer_pb2 import RunnerOutput, JobSchedulerOutput


class JobScheduler(IRunnerV2):

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        with db.session_scope() as session:
            waiting_jobs = [
                jid
                for jid, *_ in session.query(Job.id).filter(Job.state == JobState.WAITING, Job.is_disabled.is_(False))
            ]
        if waiting_jobs:
            logging.info(f'[JobScheduler] Scheduling jobs {waiting_jobs}')
        output = JobSchedulerOutput()
        for job_id in waiting_jobs:
            with db.session_scope() as session:
                # Row lock to prevent other changes
                job = session.query(Job).with_for_update().get(job_id)
                ready, message = start_job_if_ready(session, job)
                if ready:
                    if message:
                        output.failed_to_start_jobs.append(job_id)
                    else:
                        output.started_jobs.append(job_id)
                if message:
                    output.messages[job_id] = message
                session.commit()
        return RunnerStatus.DONE, RunnerOutput(job_scheduler_output=output)

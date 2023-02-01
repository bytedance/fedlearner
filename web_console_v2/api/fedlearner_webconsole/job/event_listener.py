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

from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.models import Job, JobState
from fedlearner_webconsole.job.service import JobService
from fedlearner_webconsole.k8s.event_listener import EventListener
from fedlearner_webconsole.k8s.k8s_cache import Event, ObjectType
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.workflow.service import WorkflowService
from fedlearner_webconsole.workflow.workflow_job_controller import stop_workflow


class JobEventListener(EventListener):

    def update(self, event: Event):
        # TODO(xiangyuxuan.prs): recompose the JobEventListener
        valid_obj_type = [ObjectType.FLAPP, ObjectType.SPARKAPP, ObjectType.FEDAPP]
        if event.obj_type not in valid_obj_type:
            return
        logging.debug('[k8s_watcher][job_event_listener]receive event %s', event.app_name)

        with db.session_scope() as session:
            job = session.query(Job).filter_by(name=event.app_name).first()
            if job is None:
                return
            old_state = job.state
            result_state = JobService(session).update_running_state(event.app_name)
            wid = job.workflow_id
            session.commit()

        # trigger workflow state change
        if old_state != result_state and result_state in [JobState.COMPLETED, JobState.FAILED]:
            with db.session_scope() as session:
                w = session.query(Workflow).get(wid)
                logging.info(f'[JobEventListener] {w.uuid} should be stopped.')
                if WorkflowService(session).should_auto_stop(w):
                    stop_workflow(wid)

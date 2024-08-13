# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import os
import time
import unittest
from google.protobuf.json_format import ParseDict

from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.workflow.service import WorkflowService
from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.models import JobState
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.scheduler.transaction import TransactionState
from fedlearner_webconsole.scheduler.scheduler import \
    scheduler
from fedlearner_webconsole.proto import project_pb2
from fedlearner_webconsole.job.yaml_formatter import YamlFormatterService
from testing.workflow_template.test_template_left import make_workflow_template
from testing.no_web_server_test_case import NoWebServerTestCase


class WorkflowsCommitTest(NoWebServerTestCase):

    @classmethod
    def setUpClass(cls):
        os.environ['FEDLEARNER_WEBCONSOLE_POLLING_INTERVAL'] = '0.1'

    def setUp(self):
        super().setUp()
        # Inserts project
        config = {
            'variables': [{
                'name': 'namespace',
                'value': 'leader'
            }, {
                'name': 'basic_envs',
                'value': '{}'
            }, {
                'name': 'storage_root_path',
                'value': '/'
            }]
        }

        project = Project(name='test', config=ParseDict(config, project_pb2.ProjectConfig()).SerializeToString())
        participant = Participant(name='party_leader', host='127.0.0.1', port=5000, domain_name='fl-leader.com')
        relationship = ProjectParticipant(project_id=1, participant_id=1)
        with db.session_scope() as session:
            session.add(project)
            session.add(participant)
            session.add(relationship)
            session.commit()

    @staticmethod
    def _wait_until(cond, retry_times: int = 5):
        for _ in range(retry_times):
            time.sleep(0.1)
            with db.session_scope() as session:
                if cond(session):
                    return

    def test_workflow_commit(self):
        # test the committing stage for workflow creating
        workflow_def = make_workflow_template()
        workflow = Workflow(id=20,
                            name='job_test1',
                            comment='这是一个测试工作流',
                            config=workflow_def.SerializeToString(),
                            project_id=1,
                            forkable=True,
                            state=WorkflowState.NEW,
                            target_state=WorkflowState.READY,
                            transaction_state=TransactionState.PARTICIPANT_COMMITTING,
                            creator='test_creator')
        with db.session_scope() as session:
            session.add(workflow)
            session.commit()
            WorkflowService(session).setup_jobs(workflow)
            session.commit()

        scheduler.wakeup(20)
        self._wait_until(lambda session: session.query(Workflow).get(20).state == WorkflowState.READY)
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(20)
            jobs = workflow.get_jobs(session)
            self.assertEqual(len(jobs), 2)
            self.assertEqual(jobs[0].state, JobState.NEW)
            self.assertEqual(jobs[1].state, JobState.NEW)
            # test generate job run yaml
            job_loaded_json = YamlFormatterService(session).generate_job_run_yaml(jobs[0])
            self.assertEqual(job_loaded_json['metadata']['name'], jobs[0].name)
            self.assertEqual(job_loaded_json['metadata']['labels']['owner'], workflow.creator)
            session.commit()


if __name__ == '__main__':
    unittest.main()

# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
import time
import unittest
from google.protobuf.json_format import ParseDict
from testing.common import BaseTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.models import JobState
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.scheduler.transaction import TransactionState
from fedlearner_webconsole.scheduler.scheduler import scheduler
from fedlearner_webconsole.proto import project_pb2
from workflow_template_test import make_workflow_template

class WorkflowsCommitTest(BaseTestCase):

    def get_config(self):
        config = super().get_config()
        config.START_GRPC_SERVER = False
        config.START_SCHEDULER = True
        config.START_JOB_SCHEDULER = True
        return config

    def setUp(self):
        super().setUp()
        # Inserts project
        config = {
            'domain_name': 'fl-follower.com',
            'participants': [
                {
                    'name': 'party_leader',
                    'url': '127.0.0.1:5000',
                    'domain_name': 'fl-leader.com',
                    'grpc_spec': {
                        'peer_url': '127.0.0.1:1991',
                    }
                }
            ]
        }
        project = Project(name='test',
                          config=ParseDict(config,
                                           project_pb2.Project()).SerializeToString())
        db.session.add(project)
        db.session.commit()

    def test_workflow_commit(self):
        # test the committing stage for workflow creating
        workflow_def = make_workflow_template()
        workflow = Workflow(id=20, name='job_test1', comment='这是一个测试工作流',
                            config=workflow_def.SerializeToString(),
                            project_id=1, forkable=True, state=WorkflowState.NEW,
                            target_state=WorkflowState.READY,
                            transaction_state=TransactionState.PARTICIPANT_COMMITTING)
        db.session.add(workflow)
        db.session.commit()
        scheduler.wakeup(20)
        time.sleep(1)
        workflow = Workflow.query.filter_by(id=20).first()
        self.assertEqual(workflow.state, WorkflowState.READY)
        self.assertEqual(len(workflow.jobs), 2)
        self.assertEqual(workflow.jobs[0].state, JobState.UNSPECIFIED)
        self.assertEqual(workflow.jobs[1].state, JobState.UNSPECIFIED)

        # test the committing stage for workflow running
        workflow.target_state = WorkflowState.RUNNING
        workflow.transaction_state = TransactionState.PARTICIPANT_COMMITTING
        db.session.commit()
        scheduler.wakeup(20)
        time.sleep(1)
        workflow = Workflow.query.filter_by(id=20).first()
        self.assertEqual(workflow.state, WorkflowState.RUNNING)
        self.assertEqual(workflow.jobs[0].state, JobState.STARTED)
        self.assertEqual(workflow.jobs[1].state, JobState.READY)

        # test the committing stage for workflow stopping
        workflow.target_state = WorkflowState.STOPPED
        workflow.transaction_state = TransactionState.PARTICIPANT_COMMITTING
        db.session.commit()
        scheduler.wakeup(20)
        time.sleep(1)
        workflow = Workflow.query.filter_by(id=20).first()
        self.assertEqual(workflow.state, WorkflowState.STOPPED)
        self.assertEqual(workflow.jobs[0].state, JobState.STOPPED)
        self.assertEqual(workflow.jobs[1].state, JobState.STOPPED)


if __name__ == '__main__':
    unittest.main()

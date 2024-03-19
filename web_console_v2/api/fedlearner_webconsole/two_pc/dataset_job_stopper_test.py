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

import unittest
from unittest.mock import patch, MagicMock, ANY

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.dataset.models import DatasetJob, DatasetJobKind, DatasetJobState
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.two_pc.dataset_job_stopper import DatasetJobStopper
from fedlearner_webconsole.proto.two_pc_pb2 import StopDatasetJobData, \
    TransactionData


class DatasetJobStopperTest(NoWebServerTestCase):
    _PROJECT_ID = 1
    _DATASET_JOB_ID = 1
    _WORKFLOW_ID = 1
    _DATASET_JOB_UUID = 'test_uuid'

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=self._PROJECT_ID, name='test')
            session.add(project)
            workflow = Workflow(id=self._WORKFLOW_ID, uuid=self._DATASET_JOB_UUID)
            session.add(workflow)
            session.commit()
        stop_dataset_job_data = StopDatasetJobData(dataset_job_uuid=self._DATASET_JOB_UUID)
        self.data = TransactionData(stop_dataset_job_data=stop_dataset_job_data)

    def test_prepare_no_dataset_job(self):
        with db.session_scope() as session:
            creator = DatasetJobStopper(session, tid='1', data=self.data)
            flag, _ = creator.prepare()
            self.assertFalse(flag)

    def test_prepare_state(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=self._DATASET_JOB_ID,
                                     project_id=self._PROJECT_ID,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     uuid=self._DATASET_JOB_UUID,
                                     workflow_id=self._WORKFLOW_ID,
                                     state=DatasetJobState.FAILED,
                                     kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(dataset_job)
            session.commit()
        # test prepare state failed
        with db.session_scope() as session:
            creator = DatasetJobStopper(session, tid='1', data=self.data)
            flag, _ = creator.prepare()
            self.assertFalse(flag)

        # test prepare state succeeded
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.state = DatasetJobState.PENDING
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStopper(session, tid='1', data=self.data)
            flag, _ = creator.prepare()
            self.assertTrue(flag)

        # test prepare state stop to stop
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.state = DatasetJobState.STOPPED
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStopper(session, tid='1', data=self.data)
            flag, _ = creator.prepare()
            self.assertTrue(flag)

    def test_commit_no_workflow(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=self._DATASET_JOB_ID,
                                     project_id=self._PROJECT_ID,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     uuid=self._DATASET_JOB_UUID,
                                     state=DatasetJobState.RUNNING,
                                     kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(dataset_job)
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStopper(session, tid='1', data=self.data)
            flag, _ = creator.commit()
            self.assertTrue(flag)
            session.flush()
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            self.assertEqual(dataset_job.state, DatasetJobState.STOPPED)

    @patch('fedlearner_webconsole.two_pc.dataset_job_stopper.stop_workflow_locally')
    def test_commit_state(self, mock_stop_workflow_locally: MagicMock):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=self._DATASET_JOB_ID,
                                     project_id=self._PROJECT_ID,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     uuid=self._DATASET_JOB_UUID,
                                     workflow_id=self._WORKFLOW_ID,
                                     state=DatasetJobState.STOPPED,
                                     kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(dataset_job)
            session.commit()

        # test commit state stop to stop
        with db.session_scope() as session:
            creator = DatasetJobStopper(session, tid='1', data=self.data)
            flag, _ = creator.commit()
            self.assertTrue(flag)
            mock_stop_workflow_locally.assert_not_called()
            session.flush()
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            self.assertEqual(dataset_job.state, DatasetJobState.STOPPED)
            self.assertIsNone(dataset_job.finished_at)

        # test commit state succeeded
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.state = DatasetJobState.PENDING
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStopper(session, tid='1', data=self.data)
            flag, _ = creator.commit()
            self.assertTrue(flag)
            workflow = session.query(Workflow).get(self._WORKFLOW_ID)
            mock_stop_workflow_locally.assert_called_once_with(ANY, workflow)
            session.flush()
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            self.assertEqual(dataset_job.state, DatasetJobState.STOPPED)
            self.assertIsNotNone(dataset_job.finished_at)


if __name__ == '__main__':
    unittest.main()

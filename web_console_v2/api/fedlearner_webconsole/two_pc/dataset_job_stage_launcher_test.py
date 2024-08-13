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
from unittest.mock import patch, MagicMock

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.dataset.models import DatasetJob, DatasetJobKind, DatasetJobStage, DatasetJobState
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.two_pc.dataset_job_stage_launcher import DatasetJobStageLauncher
from fedlearner_webconsole.proto.two_pc_pb2 import LaunchDatasetJobStageData, \
    TransactionData


class DatasetJobStageLauncherTest(NoWebServerTestCase):
    _PROJECT_ID = 1
    _DATASET_JOB_ID = 1
    _DATA_BATCH_ID = 1
    _DATASET_JOB_STAGE_ID = 1
    _WORKFLOW_ID = 1
    _DATASET_JOB_UUID = 'dataset_job uuid'
    _DATASET_JOB_STAGE_UUID = 'dataset_job_stage uuid'

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=self._PROJECT_ID, name='test')
            session.add(project)
            workflow = Workflow(id=self._WORKFLOW_ID, uuid=self._DATASET_JOB_UUID)
            session.add(workflow)
            session.commit()
        launch_dataset_job_stage_data = LaunchDatasetJobStageData(dataset_job_stage_uuid=self._DATASET_JOB_STAGE_UUID)
        self.data = TransactionData(launch_dataset_job_stage_data=launch_dataset_job_stage_data)

    def test_prepare_no_dataset_job_stage(self):
        with db.session_scope() as session:
            creator = DatasetJobStageLauncher(session, tid='1', data=self.data)
            flag, _ = creator.prepare()
            self.assertFalse(flag)

    def test_prepare_illegal_state(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=self._DATASET_JOB_ID,
                                     project_id=0,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     uuid=self._DATASET_JOB_UUID,
                                     workflow_id=self._WORKFLOW_ID,
                                     state=DatasetJobState.FAILED,
                                     kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(dataset_job)
            dataset_job_stage = DatasetJobStage(id=self._DATASET_JOB_STAGE_ID,
                                                project_id=self._PROJECT_ID,
                                                dataset_job_id=self._DATASET_JOB_ID,
                                                uuid=self._DATASET_JOB_STAGE_UUID,
                                                workflow_id=self._WORKFLOW_ID,
                                                data_batch_id=self._DATA_BATCH_ID,
                                                state=DatasetJobState.FAILED)
            session.add(dataset_job_stage)
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStageLauncher(session, tid='1', data=self.data)
            flag, _ = creator.prepare()
            self.assertFalse(flag)

    def test_prepare_no_related_workflow(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=self._DATASET_JOB_ID,
                                     project_id=self._PROJECT_ID,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     uuid=self._DATASET_JOB_UUID,
                                     workflow_id=0,
                                     state=DatasetJobState.PENDING,
                                     kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(dataset_job)
            dataset_job_stage = DatasetJobStage(id=self._DATASET_JOB_STAGE_ID,
                                                project_id=self._PROJECT_ID,
                                                dataset_job_id=self._DATASET_JOB_ID,
                                                uuid=self._DATASET_JOB_STAGE_UUID,
                                                workflow_id=100,
                                                data_batch_id=self._DATA_BATCH_ID,
                                                state=DatasetJobState.PENDING)
            session.add(dataset_job_stage)
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStageLauncher(session, tid='1', data=self.data)
            flag, _ = creator.prepare()
            self.assertFalse(flag)

    def test_prepare_successfully(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=self._DATASET_JOB_ID,
                                     project_id=self._PROJECT_ID,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     uuid=self._DATASET_JOB_UUID,
                                     workflow_id=self._WORKFLOW_ID,
                                     state=DatasetJobState.PENDING,
                                     kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(dataset_job)
            dataset_job_stage = DatasetJobStage(id=self._DATASET_JOB_STAGE_ID,
                                                project_id=self._PROJECT_ID,
                                                dataset_job_id=self._DATASET_JOB_ID,
                                                uuid=self._DATASET_JOB_STAGE_UUID,
                                                workflow_id=self._WORKFLOW_ID,
                                                data_batch_id=self._DATA_BATCH_ID,
                                                state=DatasetJobState.PENDING)
            session.add(dataset_job_stage)
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStageLauncher(session, tid='1', data=self.data)
            flag, _ = creator.prepare()
            self.assertTrue(flag)

        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.state = DatasetJobState.RUNNING
            dataset_job_stage = session.query(DatasetJobStage).get(self._DATASET_JOB_STAGE_ID)
            dataset_job_stage.state = DatasetJobState.RUNNING
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStageLauncher(session, tid='1', data=self.data)
            flag, _ = creator.prepare()
            self.assertTrue(flag)

    @patch('fedlearner_webconsole.two_pc.dataset_job_stage_launcher.DatasetJobStageLocalController.start')
    def test_commit(self, mock_start: MagicMock):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=self._DATASET_JOB_ID,
                                     project_id=self._PROJECT_ID,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     uuid=self._DATASET_JOB_UUID,
                                     workflow_id=self._WORKFLOW_ID,
                                     state=DatasetJobState.RUNNING,
                                     kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(dataset_job)
            dataset_job_stage = DatasetJobStage(id=self._DATASET_JOB_STAGE_ID,
                                                project_id=self._PROJECT_ID,
                                                dataset_job_id=self._DATASET_JOB_ID,
                                                uuid=self._DATASET_JOB_STAGE_UUID,
                                                workflow_id=self._WORKFLOW_ID,
                                                data_batch_id=self._DATA_BATCH_ID,
                                                state=DatasetJobState.RUNNING)
            session.add(dataset_job_stage)
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStageLauncher(session, tid='1', data=self.data)
            flag, _ = creator.commit()
            self.assertTrue(flag)
            session.commit()
            mock_start.assert_not_called()
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            self.assertEqual(dataset_job.state, DatasetJobState.RUNNING)
            dataset_job_stage = session.query(DatasetJobStage).get(self._DATASET_JOB_STAGE_ID)
            self.assertEqual(dataset_job_stage.state, DatasetJobState.RUNNING)
            self.assertIsNone(dataset_job_stage.started_at)

        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.state = DatasetJobState.PENDING
            dataset_job_stage = session.query(DatasetJobStage).get(self._DATASET_JOB_STAGE_ID)
            dataset_job_stage.state = DatasetJobState.PENDING
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStageLauncher(session, tid='1', data=self.data)
            flag, _ = creator.commit()
            self.assertTrue(flag)
            dataset_job_stage = session.query(DatasetJobStage).get(self._DATASET_JOB_STAGE_ID)
            mock_start.assert_called_once_with(dataset_job_stage)
            session.commit()

        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.state = DatasetJobState.SUCCEEDED
            dataset_job_stage = session.query(DatasetJobStage).get(self._DATASET_JOB_STAGE_ID)
            dataset_job_stage.state = DatasetJobState.SUCCEEDED
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStageLauncher(session, tid='1', data=self.data)
            flag, _ = creator.commit()
            self.assertFalse(flag)


if __name__ == '__main__':
    unittest.main()

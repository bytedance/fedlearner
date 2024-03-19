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
from fedlearner_webconsole.dataset.models import DatasetJob, DatasetJobKind, DatasetJobState, DatasetJobStage
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.two_pc.dataset_job_stage_stopper import DatasetJobStageStopper
from fedlearner_webconsole.proto.two_pc_pb2 import StopDatasetJobStageData, \
    TransactionData


class DatasetJobStageStopperTest(NoWebServerTestCase):
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
        stop_dataset_job_stage_data = StopDatasetJobStageData(dataset_job_stage_uuid=self._DATASET_JOB_STAGE_UUID)
        self.data = TransactionData(stop_dataset_job_stage_data=stop_dataset_job_stage_data)

    def test_prepare_no_dataset_job_stage(self):
        with db.session_scope() as session:
            creator = DatasetJobStageStopper(session, tid='1', data=self.data)
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
            dataset_job_stage = DatasetJobStage(id=self._DATASET_JOB_STAGE_ID,
                                                project_id=self._PROJECT_ID,
                                                dataset_job_id=self._DATASET_JOB_ID,
                                                uuid=self._DATASET_JOB_STAGE_UUID,
                                                workflow_id=self._WORKFLOW_ID,
                                                data_batch_id=self._DATA_BATCH_ID,
                                                state=DatasetJobState.FAILED)
            session.add(dataset_job_stage)
            session.commit()
        # test prepare state failed
        with db.session_scope() as session:
            creator = DatasetJobStageStopper(session, tid='1', data=self.data)
            flag, _ = creator.prepare()
            self.assertFalse(flag)

        # test prepare state succeeded
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.state = DatasetJobState.PENDING
            dataset_job_stage = session.query(DatasetJobStage).get(self._DATASET_JOB_STAGE_ID)
            dataset_job_stage.state = DatasetJobState.PENDING
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStageStopper(session, tid='1', data=self.data)
            flag, _ = creator.prepare()
            self.assertTrue(flag)

        # test prepare state stop to stop
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.state = DatasetJobState.STOPPED
            dataset_job_stage = session.query(DatasetJobStage).get(self._DATASET_JOB_STAGE_ID)
            dataset_job_stage.state = DatasetJobState.STOPPED
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStageStopper(session, tid='1', data=self.data)
            flag, _ = creator.prepare()
            self.assertTrue(flag)

    @patch('fedlearner_webconsole.two_pc.dataset_job_stage_stopper.DatasetJobStageLocalController.stop')
    def test_commit_state(self, mock_stop: MagicMock):
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
            dataset_job_stage = DatasetJobStage(id=self._DATASET_JOB_STAGE_ID,
                                                project_id=self._PROJECT_ID,
                                                dataset_job_id=self._DATASET_JOB_ID,
                                                uuid=self._DATASET_JOB_STAGE_UUID,
                                                workflow_id=self._WORKFLOW_ID,
                                                data_batch_id=self._DATA_BATCH_ID,
                                                state=DatasetJobState.STOPPED)
            session.add(dataset_job_stage)
            session.commit()

        # test commit state stop to stop
        with db.session_scope() as session:
            creator = DatasetJobStageStopper(session, tid='1', data=self.data)
            flag, _ = creator.commit()
            self.assertTrue(flag)
            mock_stop.assert_not_called()
            session.flush()
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            self.assertEqual(dataset_job.state, DatasetJobState.STOPPED)
            dataset_job_stage = session.query(DatasetJobStage).get(self._DATASET_JOB_STAGE_ID)
            self.assertEqual(dataset_job_stage.state, DatasetJobState.STOPPED)
            self.assertIsNone(dataset_job_stage.finished_at)

        # test commit state succeeded
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.state = DatasetJobState.PENDING
            dataset_job_stage = session.query(DatasetJobStage).get(self._DATASET_JOB_STAGE_ID)
            dataset_job_stage.state = DatasetJobState.PENDING
            session.commit()
        with db.session_scope() as session:
            creator = DatasetJobStageStopper(session, tid='1', data=self.data)
            flag, _ = creator.commit()
            self.assertTrue(flag)
            dataset_job_stage = session.query(DatasetJobStage).get(self._DATASET_JOB_STAGE_ID)
            mock_stop.assert_called_once_with(dataset_job_stage)


if __name__ == '__main__':
    unittest.main()

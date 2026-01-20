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
from unittest.mock import patch, PropertyMock
from datetime import datetime

from fedlearner_webconsole.job.models import Job, JobState, JobType
from fedlearner_webconsole.workflow.models import WorkflowExternalState
from fedlearner_webconsole.mmgr.models import ModelJob
from fedlearner_webconsole.dataset.delete_dependency import DatasetDeleteDependency
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobKind, DatasetJobState, DatasetType, \
    DatasetJobSchedulerState
from fedlearner_webconsole.db import db
from testing.no_web_server_test_case import NoWebServerTestCase


class DatasetDeleteDependencyTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            self.default_dataset1 = Dataset(name='default dataset1',
                                            dataset_type=DatasetType.STREAMING,
                                            comment='test comment1',
                                            path='/data/dataset/123',
                                            project_id=1,
                                            created_at=datetime(2012, 1, 14, 12, 0, 5))
            session.add(self.default_dataset1)
            self.default_dataset2 = Dataset(name='default dataset2',
                                            dataset_type=DatasetType.STREAMING,
                                            comment='test comment1',
                                            path='/data/dataset/123',
                                            project_id=1,
                                            created_at=datetime(2012, 1, 14, 12, 0, 5))
            session.add(self.default_dataset2)
            self.default_dataset3 = Dataset(name='default dataset3',
                                            dataset_type=DatasetType.STREAMING,
                                            comment='test comment1',
                                            path='/data/dataset/123',
                                            project_id=1,
                                            created_at=datetime(2012, 1, 14, 12, 0, 5))
            session.add(self.default_dataset3)
            self.default_dataset4 = Dataset(name='default dataset4',
                                            dataset_type=DatasetType.STREAMING,
                                            comment='test comment1',
                                            path='/data/dataset/123',
                                            project_id=1,
                                            created_at=datetime(2012, 1, 14, 12, 0, 5))
            session.add(self.default_dataset4)
            self.default_dataset5 = Dataset(name='default dataset5',
                                            dataset_type=DatasetType.STREAMING,
                                            comment='test comment1',
                                            path='/data/dataset/123',
                                            project_id=1,
                                            created_at=datetime(2012, 1, 14, 12, 0, 5))
            session.add(self.default_dataset5)
            session.commit()
        with db.session_scope() as session:
            parent_dataset_job1 = DatasetJob(id=1,
                                             uuid='parent_dataset_job_uuid_1',
                                             project_id=1,
                                             input_dataset_id=100,
                                             output_dataset_id=1,
                                             state=DatasetJobState.RUNNING,
                                             kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(parent_dataset_job1)
            child_dataset_job1 = DatasetJob(id=2,
                                            uuid='child_dataset_job_uuid_1',
                                            project_id=1,
                                            input_dataset_id=1,
                                            output_dataset_id=100,
                                            state=DatasetJobState.FAILED,
                                            kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(child_dataset_job1)
            parent_dataset_job2 = DatasetJob(id=3,
                                             uuid='parent_dataset_job_uuid_2',
                                             project_id=1,
                                             input_dataset_id=100,
                                             output_dataset_id=2,
                                             state=DatasetJobState.SUCCEEDED,
                                             kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(parent_dataset_job2)
            child_dataset_job2 = DatasetJob(id=4,
                                            uuid='child_dataset_job_uuid_2',
                                            project_id=1,
                                            input_dataset_id=2,
                                            output_dataset_id=100,
                                            state=DatasetJobState.PENDING,
                                            kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(child_dataset_job2)
            self.default_job1 = Job(name='test-train-job-1',
                                    state=JobState.WAITING,
                                    job_type=JobType.NN_MODEL_TRANINING,
                                    workflow_id=1,
                                    project_id=1)
            session.add(self.default_job1)
            self.default_model_job1 = ModelJob(id=1,
                                               name='test-nn-job-1',
                                               job_name=self.default_job1.name,
                                               dataset_id=3)
            session.add(self.default_model_job1)
            self.default_job2 = Job(name='test-train-job-2',
                                    state=JobState.COMPLETED,
                                    job_type=JobType.NN_MODEL_TRANINING,
                                    workflow_id=1,
                                    project_id=1)
            session.add(self.default_job2)
            self.default_model_job2 = ModelJob(id=2,
                                               name='test-nn-job-2',
                                               job_name=self.default_job2.name,
                                               dataset_id=4)
            session.add(self.default_model_job2)
            parent_dataset_job4 = DatasetJob(id=5,
                                             uuid='parent_dataset_job_uuid_4',
                                             project_id=1,
                                             input_dataset_id=100,
                                             output_dataset_id=4,
                                             state=DatasetJobState.SUCCEEDED,
                                             kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(parent_dataset_job4)
            parent_dataset_job5 = DatasetJob(id=6,
                                             uuid='parent_dataset_job_uuid_5',
                                             project_id=1,
                                             input_dataset_id=100,
                                             output_dataset_id=5,
                                             state=DatasetJobState.SUCCEEDED,
                                             kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(parent_dataset_job5)
            child_dataset_job5 = DatasetJob(id=7,
                                            uuid='child_dataset_job_uuid_5',
                                            project_id=1,
                                            input_dataset_id=5,
                                            output_dataset_id=100,
                                            state=DatasetJobState.FAILED,
                                            kind=DatasetJobKind.DATA_ALIGNMENT)
            session.add(child_dataset_job5)
            session.commit()

    def test_is_deletable(self):
        # TODO(wangzeju): Not covering all branches
        with db.session_scope() as session:
            dataset_delete_dependency = DatasetDeleteDependency(session)
            # test delete not finish dataset
            dataset1 = session.query(Dataset).get(1)
            is_deletable, msg = dataset_delete_dependency.is_deletable(dataset1)
            self.assertFalse(is_deletable)

            # test dataset wtih running dependent dataset_job
            dataset2 = session.query(Dataset).get(2)
            is_deletable, msg = dataset_delete_dependency.is_deletable(dataset2)
            self.assertFalse(is_deletable)

            # test dataset with runnable cron dataset_job
            dataset_job = session.query(DatasetJob).get(4)
            dataset_job.state = DatasetJobState.SUCCEEDED
            dataset_job.scheduler_state = DatasetJobSchedulerState.RUNNABLE
            session.flush()
            is_deletable, msg = dataset_delete_dependency.is_deletable(dataset2)
            self.assertFalse(is_deletable)
            print(msg)
            self.assertEqual(
                msg[0], 'dependent cron dataset_job is still runnable, plz stop scheduler first! dataset_jobs_id: [4]')

            # test the dataset is being used by model job
            dataset3 = session.query(Dataset).get(3)
            is_deletable, msg = dataset_delete_dependency.is_deletable(dataset3)
            self.assertFalse(is_deletable)

            # test the model job is not being used dataset
            dataset4 = session.query(Dataset).get(4)
            with patch('fedlearner_webconsole.mmgr.models.ModelJob.state', new_callable=PropertyMock) as mock_state:
                mock_state.return_value = WorkflowExternalState.COMPLETED
                is_deletable, msg = dataset_delete_dependency.is_deletable(dataset4)
                self.assertTrue(is_deletable)

            with patch('fedlearner_webconsole.mmgr.models.ModelJob.state', new_callable=PropertyMock) as mock_state:
                mock_state.return_value = WorkflowExternalState.STOPPED
                is_deletable, msg = dataset_delete_dependency.is_deletable(dataset4)
                self.assertTrue(is_deletable)

            with patch('fedlearner_webconsole.mmgr.models.ModelJob.state', new_callable=PropertyMock) as mock_state:
                mock_state.return_value = WorkflowExternalState.INVALID
                is_deletable, msg = dataset_delete_dependency.is_deletable(dataset4)
                self.assertTrue(is_deletable)

            with patch('fedlearner_webconsole.mmgr.models.ModelJob.state', new_callable=PropertyMock) as mock_state:
                mock_state.return_value = WorkflowExternalState.RUNNING
                is_deletable, msg = dataset_delete_dependency.is_deletable(dataset4)
                self.assertFalse(is_deletable)

            # test deleteble dataset
            dataset5 = session.query(Dataset).get(5)
            is_deletable, msg = dataset_delete_dependency.is_deletable(dataset5)
            self.assertTrue(is_deletable)


if __name__ == '__main__':
    unittest.main()

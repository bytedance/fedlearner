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
from unittest.mock import Mock, patch

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import Dataset, ResourceState
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.two_pc.model_job_creator import ModelJobCreator
from fedlearner_webconsole.mmgr.models import Model, ModelJob, ModelJobType, ModelJobGroup
from fedlearner_webconsole.proto.two_pc_pb2 import CreateModelJobData, \
    TransactionData


class ModelJobCreatorTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(name='project')
            model = Model(name='model', uuid='model-uuid')
            model_job_group = ModelJobGroup(name='group')
            dataset = Dataset(name='dataset', uuid='dataset-uuid', is_published=True)
            session.add_all([project, model, model_job_group, dataset])
            session.commit()
        create_model_job_data = CreateModelJobData(model_job_name='model-job',
                                                   model_job_type=ModelJobType.EVALUATION.name,
                                                   model_job_uuid='model-job-uuid',
                                                   workflow_uuid='workflow-uuid',
                                                   group_name=model_job_group.name,
                                                   algorithm_type=AlgorithmType.NN_VERTICAL.name,
                                                   model_uuid=model.uuid,
                                                   project_name=project.name,
                                                   dataset_uuid='dataset-uuid')
        self.data = TransactionData(create_model_job_data=create_model_job_data)

    @patch('fedlearner_webconsole.dataset.models.Dataset.get_frontend_state')
    def test_prepare(self, mock_get_frontend_state: Mock):
        mock_get_frontend_state.return_value = ResourceState.SUCCEEDED
        with db.session_scope() as session:
            creator = ModelJobCreator(session, tid='12', data=self.data)
            flag, message = creator.prepare()
            self.assertTrue(flag)
            # fail due to model not found
            self.data.create_model_job_data.model_uuid = 'uuid'
            flag, message = creator.prepare()
            self.assertFalse(flag)
            self.assertEqual(message, 'model uuid not found')
        with db.session_scope() as session:
            self.data.create_model_job_data.model_uuid = 'model-uuid'
            model_job = ModelJob(name='model-job')
            session.add(model_job)
            session.commit()
        with db.session_scope() as session:
            # fail due to model job with the same name
            flag, message = ModelJobCreator(session, tid='12', data=self.data).prepare()
            self.assertFalse(flag)
            self.assertEqual(message, 'model job model-job already exist')
        with db.session_scope() as session:
            self.data.create_model_job_data.group_name = 'group-1'
            self.data.create_model_job_data.model_job_name = 'model-job-1'
            flag, message = ModelJobCreator(session, tid='12', data=self.data).prepare()
            self.assertFalse(flag)
            self.assertEqual(message, 'model group group-1 not exists')
        with db.session_scope() as session:
            self.data.create_model_job_data.group_name = 'group'
            # fail due to dataset is not found
            self.data.create_model_job_data.dataset_uuid = 'dataset-uuid-1'
            flag, message = ModelJobCreator(session, tid='12', data=self.data).prepare()
            self.assertFalse(flag)
            self.assertEqual(message, 'dataset dataset-uuid-1 not exists')
        with db.session_scope() as session:
            dataset = Dataset(name='dataset-test-failed', uuid='dataset-uuid-1', is_published=False)
            session.add(dataset)
            session.commit()
            # fail due to dataset is not published
            flag, message = ModelJobCreator(session, tid='12', data=self.data).prepare()
            self.assertFalse(flag)
            self.assertEqual(message, 'dataset dataset-uuid-1 is not published')
        with db.session_scope() as session:
            mock_get_frontend_state.return_value = ResourceState.FAILED
            # fail due to dataset is not succeeded
            flag, message = ModelJobCreator(session, tid='12', data=self.data).prepare()
            self.assertFalse(flag)
            self.assertEqual(message, 'dataset dataset-uuid-1 is not succeeded')

    def test_commit(self):
        with db.session_scope() as session:
            creator = ModelJobCreator(session, tid='12', data=self.data)
            creator.commit()
            session.commit()
        with db.session_scope() as session:
            model = session.query(Model).filter_by(uuid='model-uuid').first()
            project = session.query(Project).filter_by(name='project').first()
            model_job: ModelJob = session.query(ModelJob).filter_by(name='model-job').first()
            model_job_group = session.query(ModelJobGroup).filter_by(name='group').first()
            dataset = session.query(Dataset).filter_by(uuid='dataset-uuid').first()
            self.assertEqual(model_job.uuid, 'model-job-uuid')
            self.assertEqual(model_job.model_job_type, ModelJobType.EVALUATION)
            self.assertEqual(model_job.workflow_uuid, 'workflow-uuid')
            self.assertEqual(model_job.algorithm_type, AlgorithmType.NN_VERTICAL)
            self.assertEqual(model_job.model_id, model.id)
            self.assertEqual(model_job.project_id, project.id)
            self.assertEqual(model_job.group_id, model_job_group.id)
            self.assertEqual(model_job.dataset_id, dataset.id)


if __name__ == '__main__':
    unittest.main()

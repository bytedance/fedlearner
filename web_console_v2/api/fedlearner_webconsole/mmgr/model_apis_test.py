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
import urllib.parse
from http import HTTPStatus
from datetime import datetime

from testing.common import BaseTestCase

from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.mmgr.models import Model, ModelJob, ModelJobType, ModelType
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.job.models import Job, JobType


class ModelsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            m1 = Model(name='m1', project_id=1, group_id=1, algorithm_type=AlgorithmType.NN_VERTICAL)
            m2 = Model(name='m2', project_id=1, group_id=2, algorithm_type=AlgorithmType.TREE_VERTICAL)
            m3 = Model(name='m3', project_id=1, group_id=2, algorithm_type=AlgorithmType.TREE_VERTICAL)
            session.add_all([m1, m2, m3])
            session.commit()

    def test_get_models(self):
        resp = self.get_helper('/api/v2/projects/1/models')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 3)
        resp = self.get_helper('/api/v2/projects/1/models?group_id=2')
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'm2')
        resp = self.get_helper('/api/v2/projects/1/models?keyword=1')
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'm1')
        filter_param = urllib.parse.quote('(and(group_id=1)(name~="m"))')
        resp = self.get_helper(f'/api/v2/projects/1/models?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'm1')
        resp = self.get_helper('/api/v2/projects/1/models?algorithm_type=TREE_VERTICAL')
        data = self.get_response_data(resp)
        self.assertEqual(sorted([d['name'] for d in data]), ['m2', 'm3'])


class ModelApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            job = Job(id=3, name='job', job_type=JobType.NN_MODEL_TRANINING, workflow_id=2, project_id=1)
            workflow = Workflow(id=2, name='workflow', project_id=1)
            model_job = ModelJob(id=1, name='model_job', model_job_type=ModelJobType.TRAINING, group_id=1)
            model = Model(id=1,
                          name='m1',
                          uuid='uuid',
                          project_id=1,
                          group_id=1,
                          job_id=3,
                          model_job_id=1,
                          algorithm_type=AlgorithmType.NN_VERTICAL,
                          model_type=ModelType.NN_MODEL,
                          version=1,
                          created_at=datetime(2022, 5, 10, 0, 0, 0),
                          updated_at=datetime(2022, 5, 10, 0, 0, 0))
            session.add_all([model, job, workflow, model_job])
            session.commit()

    def test_get_model(self):
        resp = self.get_helper('/api/v2/projects/1/models/1')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(
            resp, {
                'id': 1,
                'name': 'm1',
                'uuid': 'uuid',
                'algorithm_type': 'NN_VERTICAL',
                'model_path': '',
                'comment': '',
                'group_id': 1,
                'project_id': 1,
                'job_id': 3,
                'model_job_id': 1,
                'version': 1,
                'workflow_id': 2,
                'workflow_name': 'workflow',
                'job_name': 'job',
                'model_job_name': 'model_job',
                'created_at': 1652140800,
                'updated_at': 1652140800
            })

    def test_patch_model(self):
        resp = self.patch_helper('/api/v2/projects/1/models/1', data={'comment': 'comment'})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            model: Model = session.query(Model).get(1)
            self.assertEqual(model.comment, 'comment')

    def test_delete_model(self):
        resp = self.delete_helper('/api/v2/projects/1/models/1')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        with db.session_scope() as session:
            model = session.query(Model).execution_options(include_deleted=True).get(1)
            self.assertIsNotNone(model.deleted_at)


if __name__ == '__main__':
    unittest.main()

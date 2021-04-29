# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

import unittest
from unittest.mock import patch
from testing.common import BaseTestCase
from fedlearner_webconsole.mmgr.models import ModelState
from fedlearner_webconsole.job.models import Job, JobType
from fedlearner_webconsole.mmgr.apis import ModelManager
from fedlearner_webconsole.mmgr.models import Model


class ModelTest(BaseTestCase):

    @patch('fedlearner_webconsole.mmgr.apis.ModelManager.get_checkpoint_path')
    def setUp(self, mock_get_checkpoint_path):
        super().setUp()
        self.model_manager = ModelManager()
        self.train_job = Job(name='train-job',
                             job_type=JobType.TREE_MODEL_TRAINING)
        self.eval_job = Job(name='eval-job',
                            job_type=JobType.TREE_MODEL_EVALUATION)
        mock_get_checkpoint_path.return_value = 'output'
        self.model_manager.create(parent_id=None, job=self.train_job)
        model = Model.query.filter_by(job_name=self.train_job.name).one()
        self.model_manager.create(parent_id=model.id, job=self.eval_job)

    @patch('fedlearner_webconsole.job.models.Job.get_result_state', create=True)
    def test_on_job_update(self, mock_get_result_state):
        model = Model.query.filter_by(job_name=self.train_job.name).one()
        assert model.state == ModelState.COMMITTED
        mock_get_result_state.return_value = 'RUNNING'
        self.model_manager.on_job_update(self.train_job)
        assert model.state == ModelState.RUNNING
        mock_get_result_state.return_value = 'COMPLETED'
        self.model_manager.on_job_update(self.train_job)
        assert model.state == ModelState.SUCCEEDED
        mock_get_result_state.return_value = 'FAILED'
        self.model_manager.on_job_update(self.train_job)
        assert model.state == ModelState.FAILED

    def test_api(self):
        resp = self.get_helper('/api/v2/model/1')
        data = self.get_response_data(resp)
        self.assertTrue(data.get('id') == 1)

        resp = self.get_helper('/api/v2/models')
        model_list = self.get_response_data(resp)
        self.assertTrue(len(model_list) == 1)

        self.delete_helper('/api/v2/model/1')
        resp = self.get_helper('/api/v2/model/1')
        data = self.get_response_data(resp)
        self.assertTrue(data.get('state') == 'DROPPED')

    def test_get_eval(self):
        model = Model.query.filter_by(job_name=self.train_job.name).one()
        self.assertTrue(len(model.get_eval_model()) == 1)


if __name__ == '__main__':
    unittest.main()

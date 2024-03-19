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
from fedlearner_webconsole.job.models import JobType
from fedlearner_webconsole.mmgr.utils import get_exported_model_path, get_job_path, get_checkpoint_path, \
    exported_model_version_path, is_model_job


class UtilsTest(unittest.TestCase):

    def test_is_model_job(self):
        self.assertFalse(is_model_job(job_type=JobType.TRANSFORMER))
        self.assertFalse(is_model_job(job_type=JobType.RAW_DATA))
        self.assertFalse(is_model_job(job_type=JobType.DATA_JOIN))
        self.assertFalse(is_model_job(job_type=JobType.PSI_DATA_JOIN))
        self.assertTrue(is_model_job(job_type=JobType.NN_MODEL_TRANINING))
        self.assertTrue(is_model_job(job_type=JobType.NN_MODEL_EVALUATION))
        self.assertTrue(is_model_job(job_type=JobType.TREE_MODEL_TRAINING))
        self.assertTrue(is_model_job(job_type=JobType.TREE_MODEL_EVALUATION))

    def test_get_job_path(self):
        storage_root_path = '/data'
        job_name = 'train_job'
        job_path = get_job_path(storage_root_path, job_name)
        exported_path = f'{storage_root_path}/job_output/{job_name}'
        self.assertEqual(job_path, exported_path)

    def test_get_exported_model_path(self):
        job_path = '/data/job_output/train_job'
        exported_model_path = get_exported_model_path(job_path)
        expected_path = f'{job_path}/exported_models'
        self.assertEqual(exported_model_path, expected_path)

    def test_get_checkpoint_path(self):
        job_path = '/data/job_output/train_job'
        checkpoint_path = get_checkpoint_path(job_path)
        expected_path = f'{job_path}/checkpoints'
        self.assertEqual(checkpoint_path, expected_path)

    def test_exported_model_version_path(self):
        exported_model_path = '/data/model_output/uuid'
        exported_model_path_v1 = exported_model_version_path(exported_model_path, 1)
        expected_path = f'{exported_model_path}/1'
        self.assertEqual(exported_model_path_v1, expected_path)


if __name__ == '__main__':
    unittest.main()

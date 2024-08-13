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
from unittest.mock import patch

from testing.common import BaseTestCase
from testing.test_data import es_query_result
from fedlearner_webconsole.mmgr.metrics.metrics_inquirer import tree_metrics_inquirer, nn_metrics_inquirer
from fedlearner_webconsole.job.models import Job, JobType
from fedlearner_webconsole.utils.proto import to_dict

_EXPECTED_TREE_METRICS_RESULT = {
    'train': {
        'ks': {
            'steps': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            'values': [
                0.47770564314760644, 0.5349813321918623, 0.5469192171410906, 0.5596894247461416, 0.5992009702504102,
                0.6175715202967825, 0.6366317091151221, 0.6989964566835509, 0.7088535349932226, 0.7418848541057288
            ]
        },
        'recall': {
            'steps': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            'values': [
                0.40186915887850466, 0.4252336448598131, 0.45794392523364486, 0.46261682242990654, 0.5233644859813084,
                0.514018691588785, 0.5093457943925234, 0.5373831775700935, 0.5467289719626168, 0.5654205607476636
            ]
        },
        'acc': {
            'steps': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            'values': [0.857, 0.862, 0.868, 0.872, 0.886, 0.883, 0.884, 0.895, 0.896, 0.902]
        },
        'auc': {
            'steps': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            'values': [
                0.8011640626857863, 0.8377684240565029, 0.8533328577203871, 0.860663242253454, 0.8797977455946351,
                0.8921428741290338, 0.9041610187629308, 0.9179270409740553, 0.928827495184419, 0.9439282062257736
            ]
        },
        'precision': {
            'steps': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            'values': [
                0.8514851485148515, 0.8584905660377359, 0.8596491228070176, 0.8839285714285714, 0.9032258064516129,
                0.8943089430894309, 0.9083333333333333, 0.9504132231404959, 0.9435483870967742, 0.9603174603174603
            ]
        },
        'f1': {
            'steps': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            'values': [
                0.546031746031746, 0.56875, 0.5975609756097561, 0.607361963190184, 0.6627218934911242,
                0.6528189910979227, 0.6526946107784432, 0.6865671641791044, 0.6923076923076923, 0.711764705882353
            ]
        }
    },
    'confusion_matrix': {
        'tp': 121,
        'tn': 781,
        'fp': 5,
        'fn': 93
    },
    'feature_importance': {
        'x': 0.3
    },
    'eval': {}
}


class MetricsInquirerTest(BaseTestCase):

    @patch('fedlearner_webconsole.mmgr.metrics.metrics_inquirer.get_feature_importance')
    @patch('fedlearner_webconsole.mmgr.metrics.metrics_inquirer._build_es_query_body')
    def test_query_tree_metrics(self, mock_es_query, mock_get_importance):
        mock_es_query.return_value = es_query_result.fake_es_query_tree_metrics_result_v2
        mock_get_importance.return_value = {'x': 0.3}
        job = Job(name='test-job', job_type=JobType.TREE_MODEL_TRAINING)
        metrics = tree_metrics_inquirer.query(job, need_feature_importance=True)
        metrics_dict = to_dict(metrics)
        self.assertIn('train', metrics_dict)
        self.assertEqual(metrics_dict, _EXPECTED_TREE_METRICS_RESULT)

    @patch('fedlearner_webconsole.mmgr.metrics.metrics_inquirer._build_es_query_body')
    def test_query_nn_vertical_metrics(self, mock_es_query):
        mock_es_query.return_value = es_query_result.fake_es_query_nn_metrics_result_v2
        job = Job(name='test-job', job_type=JobType.NN_MODEL_TRANINING)
        metrics = nn_metrics_inquirer.query(job)
        metrics_dict = to_dict(metrics)
        self.assertIn('train', metrics_dict)
        self.assertEqual(1, len(metrics_dict['train']['loss']['values']))
        self.assertEqual(1, len(metrics_dict['train']['auc']['values']))
        self.assertIn(5.694229602813721, metrics_dict['train']['loss']['values'])
        self.assertIn(0.6585884094238281, metrics_dict['train']['auc']['values'])


if __name__ == '__main__':
    unittest.main()

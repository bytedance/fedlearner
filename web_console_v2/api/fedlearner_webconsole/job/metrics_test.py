# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
from unittest.mock import patch
from http import HTTPStatus

from testing.common import BaseTestCase, TestAppProcess
from testing.test_data import es_query_result
from fedlearner_webconsole.proto import workflow_definition_pb2
from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.job.models import Job, JobType
from fedlearner_webconsole.job.metrics import JobMetricsBuilder
from fedlearner_webconsole.utils.proto import to_dict


@unittest.skip('require es client')
class SkippedJobMetricsBuilderTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        ES_HOST = ''
        ES_PORT = 80

    class FollowerConfig(Config):
        GRPC_LISTEN_PORT = 4990

    def test_data_join_metrics(self):
        job = Job(name='multi-indices-test27', job_type=JobType.DATA_JOIN)
        import json  # pylint: disable=import-outside-toplevel
        print(json.dumps(JobMetricsBuilder(job).plot_metrics()))

    def test_nn_metrics(self):
        job = Job(name='automl-2782410011', job_type=JobType.NN_MODEL_TRANINING)
        print(JobMetricsBuilder(job).plot_metrics())

    def test_peer_metrics(self):
        proc = TestAppProcess(JobMetricsBuilderTest, 'follower_test_peer_metrics', JobMetricsBuilderTest.FollowerConfig)
        proc.start()
        self.leader_test_peer_metrics()
        proc.terminate()

    def leader_test_peer_metrics(self):
        self.setup_project('leader', JobMetricsBuilderTest.FollowerConfig.GRPC_LISTEN_PORT)
        workflow = Workflow(name='test-workflow', project_id=1)
        with db.session_scope() as session:
            session.add(workflow)
            session.commit()

        while True:
            resp = self.get_helper('/api/v2/workflows/1/peer_workflows/0/jobs/test-job/metrics')
            if resp.status_code == HTTPStatus.OK:
                break
            time.sleep(1)

    def follower_test_peer_metrics(self):
        self.setup_project('follower', JobMetricsBuilderTest.Config.GRPC_LISTEN_PORT)
        with db.session_scope() as session:
            workflow = Workflow(name='test-workflow', project_id=1, metric_is_public=True)
            workflow.set_job_ids([1])
            session.add(workflow)
            job = Job(name='automl-2782410011',
                      job_type=JobType.NN_MODEL_TRANINING,
                      workflow_id=1,
                      project_id=1,
                      config=workflow_definition_pb2.JobDefinition(name='test-job').SerializeToString())
            session.add(job)
            session.commit()

        while True:
            time.sleep(1)


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


class JobMetricsBuilderTest(unittest.TestCase):

    @patch('fedlearner_webconsole.job.metrics.es.query_nn_metrics')
    def test_query_and_plot_nn_metrics(self, mock_es_query):
        mock_es_query.return_value = es_query_result.fake_es_query_nn_metrics_result
        job = Job(name='test-job', job_type=JobType.NN_MODEL_TRANINING)
        metrics = JobMetricsBuilder(job).query_nn_metrics()
        self.assertEqual(
            to_dict(metrics), {
                'train': {
                    'loss': {
                        'steps': [
                            1645093650000.0, 1645093655000.0, 1645093660000.0, 1645093665000.0, 1645093670000.0,
                            1645093675000.0, 1645093680000.0, 1645093685000.0, 1645093690000.0, 1645093695000.0
                        ],
                        'values': [
                            1.8112774487783219, 0.8499700573859391, 0.5077963560819626, 0.4255857397157412,
                            0.3902850116000456, 0.3689204063266516, 0.34096595416776837, 0.3247630867641419,
                            0.3146447554727395, 0.3103061146461047
                        ]
                    },
                    'acc': {
                        'steps': [
                            1645093650000.0, 1645093655000.0, 1645093660000.0, 1645093665000.0, 1645093670000.0,
                            1645093675000.0, 1645093680000.0, 1645093685000.0, 1645093690000.0, 1645093695000.0
                        ],
                        'values': [
                            0.37631335140332667, 0.6482393520849722, 0.749889914331765, 0.7920331122783514,
                            0.8848890877571427, 0.8932028951744239, 0.8983024559915066, 0.9003030106425285,
                            0.9026716228326161, 0.9047519653053074
                        ]
                    }
                },
                'eval': {
                    'loss': {
                        'steps': [
                            1645093650000.0, 1645093655000.0, 1645093660000.0, 1645093665000.0, 1645093670000.0,
                            1645093675000.0, 1645093680000.0, 1645093685000.0, 1645093690000.0, 1645093695000.0
                        ],
                        'values': [
                            1.8112774487783219, 0.8499700573859391, 0.5077963560819626, 0.4255857397157412,
                            0.3902850116000456, 0.3689204063266516, 0.34096595416776837, 0.3247630867641419,
                            0.3146447554727395, 0.3103061146461047
                        ]
                    },
                    'acc': {
                        'steps': [
                            1645093650000.0, 1645093655000.0, 1645093660000.0, 1645093665000.0, 1645093670000.0,
                            1645093675000.0, 1645093680000.0, 1645093685000.0, 1645093690000.0, 1645093695000.0
                        ],
                        'values': [
                            0.37631335140332667, 0.6482393520849722, 0.749889914331765, 0.7920331122783514,
                            0.8848890877571427, 0.8932028951744239, 0.8983024559915066, 0.9003030106425285,
                            0.9026716228326161, 0.9047519653053074
                        ]
                    }
                },
                'feature_importance': {}
            })
        figs = JobMetricsBuilder(job).plot_nn_metrics(metrics)
        self.assertEqual(len(figs), 2)

    @patch('fedlearner_webconsole.job.metrics.get_feature_importance')
    @patch('fedlearner_webconsole.job.metrics.es.query_tree_metrics')
    def test_query_and_plot_tree_metrics(self, mock_es_query, mock_get_importance):
        mock_es_query.return_value = es_query_result.fake_es_query_tree_metrics_result
        mock_get_importance.return_value = {'x': 0.3}
        job = Job(name='test-job', job_type=JobType.TREE_MODEL_TRAINING)
        metrics = JobMetricsBuilder(job).query_tree_metrics(need_feature_importance=True)
        self.assertEqual(to_dict(metrics), _EXPECTED_TREE_METRICS_RESULT)
        figs = JobMetricsBuilder(job).plot_tree_metrics(metrics=metrics)
        self.assertEqual(len(figs), 6)

    @patch('fedlearner_webconsole.job.metrics.JobMetricsBuilder.query_nn_metrics')
    @patch('fedlearner_webconsole.job.metrics.JobMetricsBuilder.query_tree_metrics')
    def test_query_metrics(self, mock_tree_metrics, mock_nn_metrics):
        mock_tree_metrics.return_value = {'data': 'tree_metrics'}
        mock_nn_metrics.return_value = {'data': 'nn_metrics'}
        treejob = Job(name='test-tree-job', job_type=JobType.TREE_MODEL_TRAINING)
        metrics = JobMetricsBuilder(treejob).query_metrics()
        self.assertEqual(metrics, {'data': 'tree_metrics'})

        nnjob = Job(name='test-nn-job', job_type=JobType.NN_MODEL_TRANINING)
        metrics = JobMetricsBuilder(nnjob).query_metrics()
        self.assertEqual(metrics, {'data': 'nn_metrics'})

    @patch('fedlearner_webconsole.job.metrics.get_feature_importance')
    @patch('fedlearner_webconsole.job.metrics.es.query_tree_metrics')
    def test_query_and_plot_eval_tree_metrics(self, mock_es_query, mock_get_importance):
        mock_es_query.return_value = es_query_result.fake_es_query_eval_tree_metrics_result
        mock_get_importance.return_value = {'x': 0.3}
        job = Job(name='test-job', job_type=JobType.TREE_MODEL_TRAINING)
        metrics = JobMetricsBuilder(job).query_tree_metrics(need_feature_importance=True)
        self.assertEqual(
            to_dict(metrics), {
                'eval': {
                    'auc': {
                        'steps': [10.0],
                        'values': [0.7513349869345765]
                    },
                    'recall': {
                        'steps': [10.0],
                        'values': [0.2176754973809691]
                    },
                    'f1': {
                        'steps': [10.0],
                        'values': [0.327016797789616]
                    },
                    'ks': {
                        'steps': [10.0],
                        'values': [0.375900675399236]
                    },
                    'acc': {
                        'steps': [10.0],
                        'values': [0.8019642162921606]
                    },
                    'precision': {
                        'steps': [10.0],
                        'values': [0.6587757792451808]
                    }
                },
                'confusion_matrix': {
                    'tp': 179,
                    'tn': 2827,
                    'fp': 93,
                    'fn': 649
                },
                'feature_importance': {
                    'x': 0.3
                },
                'train': {}
            })
        figs = JobMetricsBuilder(job).plot_tree_metrics(metrics=metrics)
        self.assertEqual(len(figs), 6)


if __name__ == '__main__':
    unittest.main()

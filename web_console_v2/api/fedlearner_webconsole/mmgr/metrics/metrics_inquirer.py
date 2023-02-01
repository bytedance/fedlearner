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

import logging
from typing import List

from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.proto.metrics_pb2 import ModelJobMetrics, Metric, ConfusionMatrix
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.es import ElasticSearchClient
from fedlearner_webconsole.utils.job_metrics import get_feature_importance

_ES_INDEX_NAME = 'apm*'
_es_client = ElasticSearchClient()


def _build_es_query_body(algorithm_type: str, job_name: str, metric_list: List[str]):
    query = {
        'size': 0,
        'query': {
            'bool': {
                'must': [{
                    'term': {
                        'labels.k8s_job_name': job_name
                    }
                }]
            }
        },
        'aggs': {
            metric.upper(): {
                'filter': {
                    'term': {
                        'labels.k8s_job_name': job_name
                    }
                },
                'aggs': {
                    mode.upper(): {
                        'filter': {
                            'exists': {
                                'field': f'values.model.{mode}.{algorithm_type}.{metric}'
                            }
                        },
                        'aggs': {
                            'TOP': {
                                'top_hits': {
                                    'size':
                                        0,  # 0 means get all matching hits
                                    '_source': [
                                        f'values.model.{mode}.{algorithm_type}.{metric}', 'labels', '@timestamp'
                                    ]
                                }
                            }
                        }
                    } for mode in ('train', 'eval')
                }
            } for metric in metric_list
        }
    }
    return _es_client.search(index=_ES_INDEX_NAME, body=query, request_timeout=500)


class TreeMetricsInquirer(object):
    _CONF_METRIC_LIST = ['tp', 'tn', 'fp', 'fn']
    _TREE_METRIC_LIST = ['acc', 'auc', 'precision', 'recall', 'f1', 'ks', 'mse', 'msre', 'abs'] + _CONF_METRIC_LIST
    _ALGORITHM_TYPE = 'tree_vertical'

    def _extract_metric(self, records: dict, mode: str, metric_name: str) -> Metric:
        iter_to_values = {}
        for record in records:
            iteration = record['_source']['labels']['iteration']
            value = record['_source'][f'values.model.{mode}.{self._ALGORITHM_TYPE}.{metric_name}']
            if iteration not in iter_to_values:
                iter_to_values[iteration] = []
            iter_to_values[iteration].append(value)
        ordered_iters = sorted(iter_to_values.keys())
        values = [
            # Avg
            sum(iter_to_values[iteration]) / len(iter_to_values[iteration]) for iteration in ordered_iters
        ]
        return Metric(steps=ordered_iters, values=values)

    def _extract_confusion_matrix(self, metrics: Metric) -> ConfusionMatrix:

        def get_last_value(metric_name: str):
            metric = metrics.get(metric_name)
            if metric is not None and len(metric.values) > 0:
                return int(metric.values[-1])
            return 0

        matrix = ConfusionMatrix(
            tp=get_last_value('tp'),
            tn=get_last_value('tn'),
            fp=get_last_value('fp'),
            fn=get_last_value('fn'),
        )
        # remove confusion relevant metrics
        for key in self._CONF_METRIC_LIST:
            metrics.pop(key)
        return matrix

    def _set_confusion_metric(self, metrics: ModelJobMetrics):

        def is_training() -> bool:
            iter_vals = metrics.train.get('tp')
            if iter_vals is None:
                return False
            return len(iter_vals.values) > 0

        if is_training():
            confusion_matrix = self._extract_confusion_matrix(metrics.train)
        else:
            confusion_matrix = self._extract_confusion_matrix(metrics.eval)
        metrics.confusion_matrix.CopyFrom(confusion_matrix)
        return metrics

    def query(self, job: Job, need_feature_importance: bool = False) -> ModelJobMetrics:
        job_name = job.name
        metrics = ModelJobMetrics()
        query_result = _build_es_query_body(self._ALGORITHM_TYPE, job_name, self._TREE_METRIC_LIST)
        if 'aggregations' not in query_result:
            logging.warning(f'[METRICS] no aggregations found, job_name = {job_name}, result = {query_result}')
            return metrics
        aggregations = query_result['aggregations']
        for name in self._TREE_METRIC_LIST:
            train_item = aggregations[name.upper()]['TRAIN']['TOP']['hits']['hits']
            eval_item = aggregations[name.upper()]['EVAL']['TOP']['hits']['hits']
            if len(train_item) > 0:
                metrics.train[name].MergeFrom(self._extract_metric(train_item, 'train', name))
            if len(eval_item) > 0:
                metrics.eval[name].MergeFrom(self._extract_metric(eval_item, 'eval', name))
        self._set_confusion_metric(metrics)
        if need_feature_importance:
            metrics.feature_importance.update(get_feature_importance(job))
        return metrics


class NnMetricsInquirer(object):
    _NN_METRIC_LIST = ['auc', 'loss']
    _ALGORITHM_TYPE = 'nn_vertical'

    def _extract_metric(self, records: dict, mode: str, metric_name: str) -> Metric:
        timestamp_to_values = {}
        for record in records:
            timestamp_str = record['_source']['@timestamp']
            timestamp = to_timestamp(timestamp_str) * 1000
            value = record['_source'][f'values.model.{mode}.{self._ALGORITHM_TYPE}.{metric_name}']
            timestamp_to_values[timestamp] = []
            timestamp_to_values[timestamp].append(value)
        ordered_iters = sorted(timestamp_to_values.keys())
        values = [
            # Avg
            sum(timestamp_to_values[timestamp]) / len(timestamp_to_values[timestamp]) for timestamp in ordered_iters
        ]
        return Metric(steps=ordered_iters, values=values)

    def query(self, job: Job) -> ModelJobMetrics:
        job_name = job.name
        metrics = ModelJobMetrics()
        query_result = _build_es_query_body(self._ALGORITHM_TYPE, job_name, self._NN_METRIC_LIST)
        if 'aggregations' not in query_result:
            logging.warning(f'[METRICS] no aggregations found, job_name = {job_name}, result = {query_result}')
            return metrics
        aggregations = query_result['aggregations']
        for name in self._NN_METRIC_LIST:
            train_item = aggregations[name.upper()]['TRAIN']['TOP']['hits']['hits']
            eval_item = aggregations[name.upper()]['EVAL']['TOP']['hits']['hits']
            if len(train_item) > 0:
                metrics.train[name].MergeFrom(self._extract_metric(train_item, 'train', name))
            if len(eval_item) > 0:
                metrics.eval[name].MergeFrom(self._extract_metric(eval_item, 'eval', name))
        return metrics


tree_metrics_inquirer = TreeMetricsInquirer()
nn_metrics_inquirer = NnMetricsInquirer()

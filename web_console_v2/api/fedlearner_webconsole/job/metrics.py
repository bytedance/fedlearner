# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import mpld3
from datetime import datetime
from typing import List
from matplotlib.figure import Figure
from fedlearner_webconsole.utils.es import es
from fedlearner_webconsole.job.models import Job, JobType
from fedlearner_webconsole.utils.job_metrics import get_feature_importance
from fedlearner_webconsole.proto.metrics_pb2 import ModelJobMetrics, Metric

_CONF_METRIC_LIST = ['tp', 'tn', 'fp', 'fn']
_TREE_METRIC_LIST = ['acc', 'auc', 'precision', 'recall', 'f1', 'ks', 'mse', 'msre', 'abs'] + _CONF_METRIC_LIST
_NN_METRIC_LIST = ['acc', 'auc', 'loss', 'mse', 'abs']


class JobMetricsBuilder(object):

    def __init__(self, job: Job):
        self._job = job

    def _to_datetime(self, timestamp):
        if timestamp is None:
            return None
        return datetime.fromtimestamp(timestamp / 1000.0)

    def _is_nn_job(self):
        return self._job.job_type in [JobType.NN_MODEL_TRANINING, JobType.NN_MODEL_EVALUATION]

    def _is_tree_job(self):
        return self._job.job_type in [JobType.TREE_MODEL_TRAINING, JobType.TREE_MODEL_EVALUATION]

    def query_metrics(self):
        if self._is_tree_job():
            return self.query_tree_metrics(need_feature_importance=True)
        if self._is_nn_job():
            return self.query_nn_metrics()
        return []

    def plot_metrics(self, num_buckets=30):
        figs = []
        if self._job.job_type == JobType.DATA_JOIN:
            figs = self.plot_data_join_metrics(num_buckets)
        elif self._is_nn_job():
            metrics = self.query_nn_metrics(num_buckets)
            figs = self.plot_nn_metrics(metrics)
        elif self._is_tree_job():
            metrics = self.query_tree_metrics(False)
            figs = self.plot_tree_metrics(metrics)
        elif self._job.job_type == JobType.RAW_DATA:
            figs = self.plot_raw_data_metrics(num_buckets)
        return figs

    def plot_data_join_metrics(self, num_buckets=30):
        res = es.query_data_join_metrics(self._job.name, num_buckets)
        time_res = es.query_time_metrics(self._job.name, num_buckets, index='data_join*')
        metrics = []
        if not res['aggregations']['OVERALL']['buckets']:
            return metrics

        # plot pie chart for overall join rate
        overall = res['aggregations']['OVERALL']['buckets'][0]
        labels = ['joined', 'fake', 'unjoined']
        sizes = [overall['JOINED']['doc_count'], overall['FAKE']['doc_count'], overall['UNJOINED']['doc_count']]
        fig = Figure()
        ax = fig.add_subplot(111)
        ax.pie(sizes, labels=labels, autopct='%1.1f%%')
        metrics.append(mpld3.fig_to_dict(fig))

        # plot stackplot for event time
        by_et = res['aggregations']['EVENT_TIME']['buckets']
        et_index = [self._to_datetime(buck['key']) for buck in by_et]
        et_joined = [buck['JOINED']['doc_count'] for buck in by_et]
        et_faked = [buck['FAKE']['doc_count'] for buck in by_et]
        et_unjoined = [buck['UNJOINED']['doc_count'] for buck in by_et]
        fig = Figure()
        ax = fig.add_subplot(111)
        ax.stackplot(et_index, et_joined, et_faked, et_unjoined, labels=labels)

        twin_ax = ax.twinx()
        twin_ax.patch.set_alpha(0.0)
        et_rate = [buck['JOIN_RATE']['value'] for buck in by_et]
        et_rate_fake = [buck['JOIN_RATE_WITH_FAKE']['value'] for buck in by_et]
        twin_ax.plot(et_index, et_rate, label='join rate', color='black')
        twin_ax.plot(et_index, et_rate_fake, label='join rate w/ fake', color='#8f8f8f')  # grey color

        ax.xaxis_date()
        ax.legend()
        metrics.append(mpld3.fig_to_dict(fig))

        # plot processing time vs event time
        fig_dict = self._plot_pt_vs_et(time_res)
        metrics.append(fig_dict)

        return metrics

    def query_nn_metrics(self, num_buckets: int = 30) -> ModelJobMetrics:
        res = es.query_nn_metrics(job_name=self._job.name, metric_list=_NN_METRIC_LIST, num_buckets=num_buckets)
        metrics = ModelJobMetrics()
        aggregations = res['aggregations']
        for metric in _NN_METRIC_LIST:
            buckets = aggregations[metric]['PROCESS_TIME']['buckets']
            if len(buckets) == 0:
                continue
            times = [buck['key'] for buck in buckets]
            values = [buck['VALUE']['value'] for buck in buckets]
            # filter none value in times and values
            time_values = [(t, v) for t, v in zip(times, values) if t is not None and v is not None]
            times, values = zip(*time_values)
            if len(values) == 0:
                continue
            metrics.train[metric].steps.extend(times)
            metrics.train[metric].values.extend(values)
            metrics.eval[metric].steps.extend(times)
            metrics.eval[metric].values.extend(values)
        return metrics

    def plot_nn_metrics(self, metrics: ModelJobMetrics):
        figs = []
        for name in metrics.train:
            fig = Figure()
            ax = fig.add_subplot(111)
            timestamp = [self._to_datetime(t) for t in metrics.train[name].steps]
            values = metrics.train[name].values
            ax.plot(timestamp, values, label=name)
            ax.legend()
            figs.append(mpld3.fig_to_dict(fig))
        return figs

    @staticmethod
    def _average_value_by_iteration(metrics: [List[int], List[int]]) -> [List[int], List[int]]:
        iter_to_value = {}
        for iteration, value in zip(*metrics):
            if iteration not in iter_to_value:
                iter_to_value[iteration] = []
            iter_to_value[iteration].append(value)
        iterations = []
        values = []
        for key, value_list in iter_to_value.items():
            iterations.append(key)
            values.append(sum(value_list) / len(value_list))
        return [iterations, values]

    def _get_iter_val(self, records: dict) -> Metric:
        iterations = [item['_source']['tags']['iteration'] for item in records]
        values = [item['_source']['value'] for item in records]
        iterations, values = self._average_value_by_iteration([iterations, values])
        return Metric(steps=iterations, values=values)

    @staticmethod
    def _set_confusion_metric(metrics: ModelJobMetrics):

        def _is_training() -> bool:
            iter_vals = metrics.train.get('tp')
            if iter_vals is not None and len(iter_vals.values) > 0:
                return True
            return False

        def _get_last_values(name: str, is_training: bool) -> int:
            if is_training:
                iter_vals = metrics.train.get(name)
            else:
                iter_vals = metrics.eval.get(name)
            if iter_vals is not None and len(iter_vals.values) > 0:
                return int(iter_vals.values[-1])
            return 0

        _is_training = _is_training()
        metrics.confusion_matrix.tp = _get_last_values('tp', _is_training)
        metrics.confusion_matrix.tn = _get_last_values('tn', _is_training)
        metrics.confusion_matrix.fp = _get_last_values('fp', _is_training)
        metrics.confusion_matrix.fn = _get_last_values('fn', _is_training)
        # remove confusion relevant metrics from train metrics
        for key in _CONF_METRIC_LIST:
            metrics.train.pop(key)
            metrics.eval.pop(key)

    def query_tree_metrics(self, need_feature_importance=False) -> ModelJobMetrics:
        job_name = self._job.name
        aggregations = es.query_tree_metrics(job_name, _TREE_METRIC_LIST)['aggregations']
        metrics = ModelJobMetrics()
        for name in _TREE_METRIC_LIST:
            train_ = aggregations[name.upper()]['TRAIN']['TOP']['hits']['hits']
            eval_ = aggregations[name.upper()]['EVAL']['TOP']['hits']['hits']
            if len(train_) > 0:
                metrics.train[name].MergeFrom(self._get_iter_val(train_))
            if len(eval_) > 0:
                metrics.eval[name].MergeFrom(self._get_iter_val(eval_))
        self._set_confusion_metric(metrics)
        if need_feature_importance:
            metrics.feature_importance.update(get_feature_importance(self._job))
        return metrics

    def plot_tree_metrics(self, metrics: ModelJobMetrics):
        metric_list = set.union(set(metrics.train.keys()), set(metrics.eval.keys()))
        figs = []
        for name in metric_list:
            train_metric = metrics.train.get(name)
            eval_metric = metrics.eval.get(name)
            if train_metric is None and eval_metric is None:
                continue
            fig = Figure()
            ax = fig.add_subplot(111)
            if train_metric is not None:
                ax.plot(train_metric.steps, train_metric.values, label='train', color='blue')
            if eval_metric is not None:
                ax.plot(eval_metric.steps, eval_metric.values, label='eval', color='red')
            ax.legend()
            ax.set_title(name)
            ax.set_xlabel('iteration')
            ax.set_ylabel('value')
            figs.append(mpld3.fig_to_dict(fig))
        return figs

    def plot_raw_data_metrics(self, num_buckets=30):
        res = es.query_time_metrics(self._job.name, num_buckets)
        return [self._plot_pt_vs_et(res)]

    def _plot_pt_vs_et(self, res):
        # plot process time vs event time
        by_pt = res['aggregations']['PROCESS_TIME']['buckets']
        pt_index = [self._to_datetime(buck['key']) for buck in by_pt]
        pt_min = [
            self._to_datetime(buck['MIN_EVENT_TIME']['value']) \
            for buck in by_pt]
        pt_max = [
            self._to_datetime(buck['MAX_EVENT_TIME']['value']) \
            for buck in by_pt]
        fig = Figure()
        ax = fig.add_subplot(111)
        pt_index = [idx for idx, time in zip(pt_index, pt_min) if time is not None]
        ax.plot(pt_index, list(filter(lambda x: x is not None, pt_min)), label='min event time')
        ax.plot(pt_index, list(filter(lambda x: x is not None, pt_max)), label='max event time')

        ax.xaxis_date()
        ax.yaxis_date()
        ax.legend()
        return mpld3.fig_to_dict(fig)

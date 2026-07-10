# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
from datetime import datetime

import mpld3
from matplotlib.figure import Figure

from fedlearner_webconsole.job.models import JobType
from fedlearner_webconsole.utils.es import es


class JobMetricsBuilder(object):
    def __init__(self, job):
        self._job = job

    def _to_datetime(self, timestamp):
        if timestamp is None:
            return None
        return datetime.fromtimestamp(timestamp/1000.0)

    def plot_metrics(self, num_buckets=30):
        if self._job.job_type == JobType.DATA_JOIN:
            metrics = self.plot_data_join_metrics(num_buckets)
        elif self._job.job_type in [
                JobType.NN_MODEL_TRAINING, JobType.NN_MODEL_EVALUATION]:
            metrics = self.plot_nn_metrics(num_buckets)
        elif self._job.job_type in [JobType.TREE_MODEL_TRAINING,
                                    JobType.TREE_MODEL_EVALUATION]:
            metrics = self.plot_tree_metrics()
        elif self._job.job_type == JobType.RAW_DATA:
            metrics = self.plot_raw_data_metrics(num_buckets)
        else:
            metrics = []
        return metrics

    def plot_data_join_metrics(self, num_buckets=30):
        res = es.query_data_join_metrics(self._job.name, num_buckets)
        time_res = es.query_time_metrics(self._job.name, num_buckets,
                                         index='data_join*')
        metrics = []
        if not res['aggregations']['OVERALL']['buckets']:
            return metrics

        # plot pie chart for overall join rate
        overall = res['aggregations']['OVERALL']['buckets'][0]
        labels = ['joined', 'fake', 'unjoined']
        sizes = [
            overall['JOINED']['doc_count'], overall['FAKE']['doc_count'],
            overall['UNJOINED']['doc_count']]
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
        ax.stackplot(
            et_index, et_joined, et_faked, et_unjoined, labels=labels)

        twin_ax = ax.twinx()
        twin_ax.patch.set_alpha(0.0)
        et_rate = [buck['JOIN_RATE']['value'] for buck in by_et]
        et_rate_fake = [buck['JOIN_RATE_WITH_FAKE']['value'] for buck in by_et]
        twin_ax.plot(et_index, et_rate, label='join rate', color='black')
        twin_ax.plot(et_index, et_rate_fake,
                     label='join rate w/ fake', color='#8f8f8f')  # grey color

        ax.xaxis_date()
        ax.legend()
        metrics.append(mpld3.fig_to_dict(fig))

        # plot processing time vs event time
        fig_dict = self._plot_pt_vs_et(time_res)
        metrics.append(fig_dict)

        return metrics

    def plot_nn_metrics(self, num_buckets=30):
        res = es.query_nn_metrics(self._job.name, num_buckets)
        metrics = []
        if not res['aggregations']['PROCESS_TIME']['buckets']:
            return metrics

        buckets = res['aggregations']['PROCESS_TIME']['buckets']
        time = [self._to_datetime(buck['key']) for buck in buckets]

        # plot auc curve
        auc = [buck['AUC']['value'] for buck in buckets]
        fig = Figure()
        ax = fig.add_subplot(111)
        ax.plot(time, auc, label='auc')
        ax.legend()
        metrics.append(mpld3.fig_to_dict(fig))

        return metrics

    def plot_tree_metrics(self):
        metric_list = ['acc', 'auc', 'precision', 'recall',
                       'f1', 'ks', 'mse', 'msre', 'abs']
        metrics = []
        aggregations = es.query_tree_metrics(self._job.name, metric_list)
        for name in metric_list:
            train_ = aggregations[name.upper()]['TRAIN']['TOP']['hits']['hits']
            eval_ = aggregations[name.upper()]['EVAL']['TOP']['hits']['hits']
            if len(train_) == 0 and len(eval_) == 0:
                continue
            fig = Figure()
            ax = fig.add_subplot(111)
            if len(train_) > 0:
                train_metric = [(item['_source']['tags']['iteration'],
                                 item['_source']['value'])
                                for item in train_]
                ax.plot(*zip(*train_metric), label='train', color='blue')
            if len(eval_) > 0:
                eval_metric = [(item['_source']['tags']['iteration'],
                                item['_source']['value'])
                               for item in eval_]
                ax.plot(*zip(*eval_metric), label='eval', color='red')
            ax.legend()
            ax.set_title(name)
            ax.set_xlabel('iteration')
            ax.set_ylabel('value')
            metrics.append(mpld3.fig_to_dict(fig))
        return metrics

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
        pt_index = [
            idx for idx, time in zip(pt_index, pt_min) if time is not None
        ]
        ax.plot(
            pt_index,
            list(filter(lambda x: x is not None, pt_min)),
            label='min event time'
        )
        ax.plot(
            pt_index,
            list(filter(lambda x: x is not None, pt_max)),
            label='max event time'
        )

        ax.xaxis_date()
        ax.yaxis_date()
        ax.legend()
        return mpld3.fig_to_dict(fig)

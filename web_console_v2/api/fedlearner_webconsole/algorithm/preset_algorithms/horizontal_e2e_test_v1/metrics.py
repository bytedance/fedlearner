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

import os
import tensorflow as tf
from fedlearner.common import metrics
from fedlearner.fedavg.master import LeaderMaster, FollowerMaster
from fedlearner.fedavg.cluster.cluster_spec import FLClusterSpec
from fedlearner.fedavg._global_context import global_context as _gtx


class MetricsKerasCallback(tf.keras.callbacks.Callback):

    def __init__(self):
        super().__init__()
        self._global_step = None
        self._metrics = {}

    def on_train_end(self, logs=None):
        self.emit_metrics()

    def on_train_batch_end(self, batch, logs=None):
        self.update_metrics(logs)

    def on_test_end(self, logs=None):
        self.emit_metrics()

    def on_test_batch_end(self, batch, logs=None):
        self.update_metrics(logs)

    def update_metrics(self, logs: dict):
        if 'batch' not in logs:
            return

        self._global_step = logs['batch']
        self._metrics = logs
        if self._global_step % 10 == 0:
            self.emit_metrics()

    def emit_metrics(self):
        if self._global_step is None:
            return
        stats_pipe = _gtx.stats_client.pipeline()
        stats_pipe.gauge('trainer.metric_global_step', self._global_step)
        for key, value in self._metrics.items():
            if key in ('size', 'batch'):
                continue
            stats_pipe.gauge('trainer.metric_value', value, tags={'metric': key})
            metrics.emit_store(name=key, value=value)
        stats_pipe.send()

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
# limitations under the License

import re
import tensorflow.compat.v1 as tf
from tensorflow.python.training import training_util # pylint: disable=no-name-in-module
from fedlearner.common import metrics
from fedlearner.common.metric_collector import metric_collector
from fedlearner.trainer._global_context import global_context as _gctx

class GlobalStepMetricTensorHook(tf.train.SessionRunHook):
    """ Send metric every secs or steps by stats_client. """
    def __init__(self,
                 tensor_dict=None,
                 every_secs=None,
                 every_steps=None,
                 stats_client=None):
        """
        Args:
            tensors: `dict` that maps name to metric_tensor pair.
        """
        if not isinstance(tensor_dict, dict):
            raise TypeError("tensors not a dict")
        if not tensor_dict:
            raise ValueError("tensors is empty")
        self._metric_names = []
        for name, tensor in tensor_dict.items():
            if not isinstance(name, str) or not name:
                raise ValueError("uninvalid metric name, "
                                 "name: %s, type: %s"%(name, type(name)))
            if not tf.is_tensor(tensor) \
                or not (tensor.dtype.is_floating or tensor.dtype.is_integer):
                raise ValueError("uninvalid metric tensor, "
                                 "name: %s, tensor: %s" % (name, tensor))
            self._metric_names.append(name)
        self._tensor_dict = tensor_dict
        self._stats_client = stats_client or _gctx.stats_client
        self._timer = tf.train.SecondOrStepTimer(
            every_secs=every_secs, every_steps=every_steps)

    def begin(self):
        g = tf.get_default_graph()
        for _, tensor in self._tensor_dict.items():
            if tensor.graph != g:
                raise ValueError("metric tensor %s graph not equal "
                       "to current graph %s." % (tensor, g))
        self._next_step = None
        self._global_step_tensor = \
            training_util._get_or_create_global_step_read() # pylint: disable=protected-access
        if self._global_step_tensor is None:
            raise RuntimeError("Global step should be created "
                               "to use GlobalStepTensorStatsHook.")
        self._global_step_key = "global_step"
        i = 0
        while self._global_step_key in self._tensor_dict:
            self._global_step_key = "global_step_" + str(i)
            i += 1
        self._tensor_dict[self._global_step_key] = self._global_step_tensor

    def before_run(self, run_context):
        self._should_trigger = self._next_step is not None \
            and self._timer.should_trigger_for_step(self._next_step)
        if self._should_trigger:
            return tf.train.SessionRunArgs(fetches=self._tensor_dict)
        return tf.train.SessionRunArgs(fetches=self._global_step_tensor)

    def after_run(self, run_context, run_values):
        if self._should_trigger:
            global_step = run_values.results[self._global_step_key]
            self._stats_metric(global_step, run_values.results)
            self._timer.update_last_triggered_step(global_step)
        else:
            global_step = run_values.results

        self._next_step = global_step + 1

    def _stats_metric(self, global_step, results):
        with self._stats_client.pipeline() as pipe:
            name_prefix = 'model.train.nn_vertical'
            metric_collector.emit_store(
                f'{name_prefix}.global_step', global_step)
            for key in self._metric_names:
                value = results[key]
                pipe.gauge("trainer.metric_value",
                           value.sum(),
                           tags={"metric": key})

                # for compatibility, also write to metrics(es)
                metrics.emit_store(name=key, value=value)

                metric_collector.emit_store(
                    f'{name_prefix}.{key}', value.sum())
                # for compatibility, also emit one with metric name in tags
                metric_collector.emit_store(f'{name_prefix}.metric_value',
                                            value.sum(), tags={'metric': key})


class StepMetricsHook(GlobalStepMetricTensorHook):
    """
        Deprecated. Use `GlobalStepMetricTensorHook` instead.
    """
    def __init__(self, tensor_dict=None, every_n_iter=5, tags_dict=None):
        super(StepMetricsHook, self).__init__(tensor_dict,
                                              every_steps=every_n_iter)


class StepLossAucMetricsHook(GlobalStepMetricTensorHook):
    """
        Deprecated. Use `GlobalStepMetricTensorHook` instead.
    """
    def __init__(self, loss_tensor, auc_tensor, every_n_iter=5,
                 event_time_tensor=None):
        tensor_dict = {"loss": loss_tensor,
                       "auc": auc_tensor}
        super(StepLossAucMetricsHook, self).__init__(tensor_dict,
                                                     every_steps=every_n_iter)


# NOTE(whisylan): maybe lead to memory leak
class TraceStatsHook(tf.train.SessionRunHook):
    def __init__(self,
                 timing_topn=20,
                 timing_min_ms=100,
                 memory_topn=20,
                 memory_min_bytes=1024*1024,
                 every_secs=None,
                 every_steps=None,
                 stats_client=None):
        self._timing_topn = timing_topn
        self._timing_min_ms = timing_min_ms
        self._memory_topn = memory_topn
        self._memory_min_bytes = memory_min_bytes
        self._stats_client = stats_client or _gctx.stats_client
        self._timer = tf.train.SecondOrStepTimer(
            every_secs=every_secs, every_steps=every_steps)
        self._run_options = \
            tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)

    def begin(self):
        self._next_step = None
        self._global_step_tensor = \
            training_util._get_or_create_global_step_read() # pylint: disable=protected-access
        if self._global_step_tensor is None:
            raise RuntimeError("Global step should be created "
                               "to use TraceStatsHook.")

    def before_run(self, run_context):
        self._should_trigger = self._next_step is not None \
            and self._timer.should_trigger_for_step(self._next_step)

        return tf.train.SessionRunArgs(
            fetches=self._global_step_tensor,
            options=self._run_options if self._should_trigger else None)

    def after_run(self, run_context, run_values):
        global_step = run_values.results
        if self._should_trigger:
            global_step = run_context.session.run(self._global_step_tensor)
            self._emit_stats(run_values.run_metadata.step_stats)
            self._timer.update_last_triggered_step(global_step)

        self._next_step = global_step + 1

    def _emit_stats(self, step_stats):
        # parse events
        events = []
        for dev_stats in step_stats.dev_stats:
            for node_stats in dev_stats.node_stats:
                # op event
                ev = dict()
                ev["op_name"] = node_stats.node_name
                if node_stats.node_name == "RecvTensor":
                    op = "RecvTensor"
                else:
                    _, op, _ = self._parse_op_label(node_stats.timeline_label)
                ev["op"] = op
                ev["duration"] = (node_stats.op_end_rel_micros \
                    - node_stats.op_start_rel_micros) / 1000
                # mem event
                num_bytes = 0
                for output in node_stats.output:
                    num_bytes += output.tensor_description\
                        .allocation_description.requested_bytes
                ev["output_bytes"] = num_bytes
                events.append(ev)

        with self._stats_client.pipeline() as pipe:
            # TODO(lixiaoguang.01) old version, to be deleted
            # emit op
            pipe.gauge("trainer.trace.op_count", len(events))
            events.sort(key=lambda ev: ev["duration"], reverse=True)
            # new version
            name_prefix = 'model.trace.nn_vertical'
            metric_collector.emit_store(f'{name_prefix}.op_count', len(events))
            for ev in events[0:self._timing_topn]:
                if ev["duration"] < self._timing_min_ms:
                    break
                pipe.timing("trainer.trace.op_timing",
                            ev["duration"],
                            tags={"op_name": ev["op_name"], "op": ev["op"]})
                metric_collector.emit_store(
                    f'{name_prefix}.op_timing',
                    ev["duration"],
                    {"op_name": ev["op_name"], "op": ev["op"]}
                )

            # emit memory
            events.sort(key=lambda ev: ev["output_bytes"], reverse=True)
            for ev in events[0:self._memory_topn]:
                if ev["output_bytes"] < self._memory_min_bytes:
                    break
                pipe.gauge("trainer.trace.op_output_bytes",
                           ev["output_bytes"],
                           tags={"op_name": ev["op_name"], "op": ev["op"]})
                metric_collector.emit_store(
                    f'{name_prefix}.op_output_bytes',
                    ev["output_bytes"],
                    {"op_name": ev["op_name"], "op": ev["op"]}
                )

    def _parse_op_label(self, label):
        """
        Parses the fields in a node timeline label.
        Copy from tensorflow.timeline
        """
        # Expects labels of the form: name = op(arg, arg, ...).
        match = re.match(r'(.*) = (.*)\((.*)\)', label)
        if match is None:
            return 'unknown', 'unknown', []
        nn, op, inputs = match.groups()
        if not inputs:
            inputs = []
        else:
            inputs = inputs.split(', ')
        return nn, op, inputs
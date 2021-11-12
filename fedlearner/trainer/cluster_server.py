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

import tensorflow.compat.v1 as tf
from fedlearner.common import fl_logging, common


class ClusterServer():
    def __init__(self,
                 cluster_spec,
                 job_name,
                 task_index=0,
                 extra_reserve_jobs=None):
        self._job_name = job_name
        self._task_index = task_index
        self._extra_reserve_jobs = set(extra_reserve_jobs) \
            if extra_reserve_jobs is not None else set(["ps"])
        self._create_tf_server(cluster_spec)

    def _create_tf_server(self, cluster_spec):
        self._tf_config = tf.ConfigProto()
        tf_config = common.get_tf_config()
        self._tf_config.inter_op_parallelism_threads = \
            tf_config["inter_op_parallelism_threads"]
        self._tf_config.intra_op_parallelism_threads = \
            tf_config["intra_op_parallelism_threads"]
        self._tf_config.experimental \
            .share_session_state_in_clusterspec_propagation = True
        self._tf_config.rpc_options.compression_algorithm = "gzip"
        self._tf_config.rpc_options.cache_rpc_response = True
        self._tf_config.rpc_options.disable_session_connection_sharing = True

        try:
            address = cluster_spec.task_address(
                self._job_name, self._task_index)
            self._tf_server = \
                tf.distribute.Server({"server": {
                                        self._task_index: address}
                                     },
                                     protocol="grpc",
                                     config=self._tf_config)
            self._tf_target = "grpc://" + address
        except ValueError:
            self._tf_server = \
                tf.distribute.Server({"server":
                                        {self._task_index: "localhost:0"}
                                     },
                                     protocol="grpc",
                                     config=self._tf_config)
            self._tf_target = self._tf_server.target

        # modify cluster_spec
        cluster_dict = dict()
        cluster_dict[self._job_name] = {
            self._task_index: self._tf_target[len("grpc://"):]
        }
        for job_name in cluster_spec.jobs:
            if job_name == self._job_name:
                continue
            if job_name in self._extra_reserve_jobs:
                cluster_dict[job_name] = cluster_spec.job_tasks(job_name)

        self._tf_cluster_spec = tf.train.ClusterSpec(cluster_dict)
        self._tf_config.cluster_def.CopyFrom(
            self._tf_cluster_spec.as_cluster_def())

        fl_logging.info("cluster server target: %s\nconfig: \n%s",
                        self._tf_target, self._tf_config)

    @property
    def target(self):
        return self._tf_target

    @property
    def cluster_spec(self):
        return self._tf_cluster_spec

    @property
    def cluster_config(self):
        return self._tf_config

    @property
    def worker_num(self):
        pass

    @property
    def ps_num(self):
        pass

    @property
    def device_setter(self):
        return tf.train.replica_device_setter(
            worker_device="/job:%s/task:%d"%(self._job_name, self._task_index),
            cluster=self._tf_cluster_spec)

    def join(self):
        self._tf_server.join()

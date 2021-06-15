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
# pylint: disable=protected-access

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow.compat.v1 as tf
from fedlearner.trainer import operator


def _sharded_size(total_size, shard_id, num_shards):
    return int(total_size / num_shards) + ((total_size % num_shards) > shard_id)


class Embedding(object):
    def __init__(self, config, devices=(None,)):
        self._config = config
        self._devices = devices
        self._num_shards = len(devices)
        self._use_fid_v2 = config['use_fid_v2']

        self._weights = []
        with tf.variable_scope("lagrange_embedding_pooling/%s"%config['name']):
            for i in range(config['num_groups']):
                shards = []
                for shard_id in range(self._num_shards):
                    with tf.device(self._devices[shard_id]), \
                                   tf.variable_scope('shard_%d'%shard_id):
                        weight_name = 'embedding_weight_' + '_'.join([
                            str(j) for j, k in enumerate(
                                config['slot_weight_index']) if k == i])
                        shards.append(tf.get_variable(
                            name=weight_name,
                            shape=(_sharded_size(config['weight_hash_sizes'][i],
                                                 shard_id, self._num_shards),
                                   config['weight_sizes'][i]),
                            initializer=config['initializers'][i]
                        ))
                self._weights.append(shards)

    @property
    def weights(self):
        return self._weights

    @property
    def config(self):
        return self._config

    def _lookup_one_shard(self, features, shard_id):
        name = self._config['name']

        slot_size = tf.constant(self._config['slot_size'], dtype=tf.int64)
        slot_weight_index = tf.constant(self._config['slot_weight_index'],
                                        dtype=tf.int64)
        slot_output_offset = tf.constant(self._config['slot_output_offset'],
                                         dtype=tf.int64)
        slot_hash_size = tf.constant(self._config['slot_hash_size'],
                                     dtype=tf.int64)
        slot_weight_offset = tf.constant(self._config['slot_weight_offset'],
                                         dtype=tf.int64)

        fmt = '%s_%d_'%(name, shard_id)

        num_unique_fids_per_partition = features.pop(
            fmt+'num_unique_fids_per_partition')
        fid_to_unique_index = features.pop(fmt+'fid_to_unique_index')
        unique_fid_hash = features.pop(fmt+'unique_fid_hash')
        assert isinstance(unique_fid_hash, tuple)
        batch_size = features.pop(fmt+'batch_size')
        instance_ids = features.pop(fmt+'instance_ids')
        fids = features.pop(fmt+'fids')

        bwd_deps = [
            tf.identity(num_unique_fids_per_partition,
                        name="%s_Identity_num_unique_fids_per_partition"%(fmt)),
            tf.identity(fid_to_unique_index,
                        name="%s_Identity_fid_to_unique_index"%(fmt)),] + [
            tf.identity(t, name="%s_Identity_unique_fid_hash_%d"%(fmt, i)) \
                for (i, t) in enumerate(unique_fid_hash)]

        with tf.control_dependencies(bwd_deps):
            output = operator.lagrange_lite_ops.lagrange_embedding_pooling(
                output_size=self._config['output_size'],
                weight_sizes=self._config['weight_sizes'],
                use_fid_v2=self._use_fid_v2,
                num_shards=self._num_shards,
                batch_size=batch_size,
                instance_ids=instance_ids,
                fids=fids,
                slot_size=slot_size,
                slot_weight_index=slot_weight_index,
                slot_output_offset=slot_output_offset,
                slot_hash_size=slot_hash_size,
                slot_weight_offset=slot_weight_offset,
                weights=[w[shard_id] for w in self.weights])

        return output

    def lookup(self, features):
        if self._num_shards == 1:
            with tf.device(self._devices[0]):
                return self._lookup_one_shard(features, 0)

        outputs = []
        for shard_id in range(self._num_shards):
            with tf.device(self._devices[shard_id]):
                outputs.append(self._lookup_one_shard(features, shard_id))
        return tf.add_n(outputs)

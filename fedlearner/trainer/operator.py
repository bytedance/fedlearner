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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

import tensorflow.compat.v1 as tf

_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

_CPU_LIB_PATH = os.path.join(_HOME, 'cc/embedding.so')

class custom_fedlearner_operators_failed_to_load(object):
    pass

lagrange_lite_ops = custom_fedlearner_operators_failed_to_load

path = _CPU_LIB_PATH

if os.path.exists(path):
    lagrange_lite_ops = tf.load_op_library(path)


if lagrange_lite_ops is custom_fedlearner_operators_failed_to_load:
    print("Failed to load fedlearner operators from %s"%path)


def _multidevice_preprocess_fids(fids, config, num_shards):
    name = config['name']
    with tf.name_scope("lagrange_multidevice_preprocess_fid/%s"%name):
        slot_weight_index = tf.constant(config['slot_weight_index'],
                                       dtype=tf.int64)
        slot_hash_size = tf.constant(config['slot_hash_size'], dtype=tf.int64)
        slot_weight_offset = tf.constant(config['slot_weight_offset'],
                                        dtype=tf.int64)

        ret = lagrange_lite_ops.lagrange_multi_device_preprocess_fid(
            num_weights=config['num_groups'],
            num_shards=num_shards,
            use_fid_v2=config['use_fid_v2'],
            total_weights=num_shards*config['num_groups'],
            instance_ids=fids.indices,
            fids=fids.values,
            slot_weight_index=slot_weight_index,
            slot_hash_size=slot_hash_size,
            slot_weight_offset=slot_weight_offset)

    features = {}
    for i in range(num_shards):
        fmt = '%s_%d_'%(name, i)
        features.update({
            fmt+'batch_size': fids.dense_shape[0],
            fmt+'instance_ids': ret[0][i],
            fmt+'fids': ret[1][i],
            fmt+'num_unique_fids_per_partition': ret[2][i],
            fmt+'fid_to_unique_index': ret[3][i],
            fmt+'unique_fid_hash':
                tuple(ret[4][i*config['num_groups']:(i+1)*config['num_groups']])
        })
    return features


@tf.RegisterGradient("LagrangeEmbeddingPooling")
def _embedding_pooling_gradient(op, grad):
    num_weights = op.get_attr("num_weights")
    control_inputs = op.control_inputs
    if not control_inputs:
        # tf 2.0 graph
        read_variable_op = op.name + "/ReadVariableOp:"
        control_inputs = [t.op.control_inputs for t in op.inputs \
                                    if t.name.startswith(read_variable_op)]
        assert len(control_inputs) == 1
        control_inputs = control_inputs[0]

    def _get_control_input_by_name(name):
        candidates = [x for x in control_inputs if x.name.find(name) != -1]
        assert len(candidates) == 1
        return candidates[0].outputs[0]

    num_unique_fids_per_partition = _get_control_input_by_name(
        'num_unique_fids_per_partition')
    fid_to_unique_index = _get_control_input_by_name('fid_to_unique_index')
    unique_fid_hash = [_get_control_input_by_name('unique_fid_hash_%d'%i) \
        for i in range(num_weights)]

    assert len(unique_fid_hash) == num_weights

    values = lagrange_lite_ops.lagrange_embedding_unpooling(
        num_weights=num_weights,
        weight_sizes=op.get_attr('weight_sizes'),
        use_fid_v2=op.get_attr('use_fid_v2'),
        output_grad=grad,
        instance_ids=op.inputs[1],
        fids=op.inputs[2],
        fid_to_unique_index=fid_to_unique_index,
        num_unique_fids_per_partition=num_unique_fids_per_partition,
        slot_size=op.inputs[3],
        slot_weight_index=op.inputs[4],
        slot_output_offset=op.inputs[5])

    weight_grads = []
    for i, (k, v) in enumerate(zip(unique_fid_hash, values)):
        w = op.inputs[8+i]
        shape = tf.shape(w, out_type=tf.int64)
        weight_grads.append(
            tf.IndexedSlices(indices=k, values=v, dense_shape=shape))

    return [None for i in range(8)] + weight_grads

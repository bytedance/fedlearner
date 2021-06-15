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

import tensorflow.compat.v1 as tf

from fedlearner.trainer import embedding
from fedlearner.trainer import estimator
from fedlearner.trainer import feature
from fedlearner.trainer import operator
from fedlearner.trainer import utils


class ConfigRunError(Exception):
    pass


class SparseFLModel(estimator.FLModel):
    def __init__(self, role, bridge, example_ids, exporting=False,
                 config_run=True,
                 bias_tensor=None, vec_tensor=None,
                 bias_embedding=None, vec_embedding=None,
                 feature_columns=None):
        super(SparseFLModel, self).__init__(role,
            bridge, example_ids, exporting)

        self._config_run = config_run
        self._num_shards = 1
        if config_run:
            self._bias_tensor = tf.placeholder(tf.float32, shape=[None, None])
            self._vec_tensor = tf.placeholder(tf.float32, shape=[None, None])
        else:
            self._bias_tensor = bias_tensor
            self._vec_tensor = vec_tensor
        self._bias_embedding = bias_embedding
        self._vec_embedding = vec_embedding
        self._feature_columns = feature_columns

        self._frozen = False
        self._slot_ids = []
        self._feature_slots = {}
        self._feature_column_v1s = {}
        self._use_fid_v2 = False
        self._num_embedding_groups = 3

    def add_feature_slot(self, *args, **kwargs):
        assert not self._frozen, "Cannot modify model after finalization"
        fs = feature.FeatureSlot(*args, **kwargs)
        if self._use_fid_v2:
            assert 0 <= fs.slot_id < utils.MAX_SLOTS_v2, \
            "Invalid slot id %d"%fs.slot_id
        else:
            assert 0 <= fs.slot_id < utils.MAX_SLOTS, \
            "Invalid slot id %d"%fs.slot_id
        self._slot_ids.append(fs.slot_id)
        self._feature_slots[fs.slot_id] = fs
        return fs

    def add_feature_column(self, *args, **kwargs):
        assert not self._frozen, "Cannot modify model after finalization"
        fc = feature.FeatureColumnV1(*args, **kwargs)
        slot_id = fc.feature_slot.slot_id
        assert slot_id in self._feature_slots and \
            self._feature_slots[slot_id] is fc.feature_slot, \
            "FeatureSlot with id %d must be added to Model first"%slot_id
        assert slot_id not in self._feature_column_v1s, \
            "Only one FeatureColumnV1 can be created for each slot"
        self._feature_column_v1s[slot_id] = fc
        return fc

    def set_use_fid_v2(self, use_fid_v2):
        self._use_fid_v2 = use_fid_v2

    def get_bias(self):
        assert self._frozen, "Cannot get bias before freeze_slots"
        return self._bias_tensor

    def get_vec(self):
        assert self._frozen, "Cannot get vector before freeze_slots"
        return self._vec_tensor

    def _get_bias_slot_configs(self):
        if not self._config_run:
            return self._bias_embedding.config if self._bias_embedding else None

        slot_list = []
        fs_map = {}
        for slot_id in self._slot_ids:
            fs = self._feature_slots[slot_id]
            key = (id(fs._bias_initializer), id(fs._bias_optimizer))
            fs_map[key] = fs
            slot_list.append((fs.slot_id, 1, fs.hash_table_size, key))
        if not slot_list:
            return None

        bias_config = utils._compute_slot_config(slot_list, 1,
            self._use_fid_v2)
        bias_config['name'] = 'bias'
        bias_config['slot_list'] = slot_list
        bias_config['initializers'] = [fs_map[i]._bias_initializer
            for i in bias_config['weight_group_keys']]
        bias_config['optimizers'] = [fs_map[i]._bias_optimizer
            for i in bias_config['weight_group_keys']]
        bias_config['use_fid_v2'] = self._use_fid_v2
        return bias_config

    def _get_vec_slot_configs(self):
        if not self._config_run:
            return self._vec_embedding.config if self._vec_embedding else None

        slot_list = []
        fs_map = {}
        for slot_id in self._slot_ids:
            if slot_id not in self._feature_column_v1s:
                continue
            fc = self._feature_column_v1s[slot_id]
            fs = fc.feature_slot
            if fc.feature_slot.dim > 1:
                key = (id(fs._vec_initializer), id(fs._vec_optimizer))
                fs_map[key] = fs
                slot_list.append((slot_id, fs.dim - 1, fs.hash_table_size, key))
        if not slot_list:
            return None

        vec_config = utils._compute_slot_config(slot_list,
            self._num_embedding_groups,
            self._use_fid_v2)
        vec_config['name'] = 'vec'
        vec_config['slot_list'] = slot_list
        vec_config['initializers'] = [fs_map[i]._vec_initializer
            for i in vec_config['weight_group_keys']]
        vec_config['optimizers'] = [fs_map[i]._vec_optimizer
            for i in vec_config['weight_group_keys']]
        vec_config['use_fid_v2'] = self._use_fid_v2
        return vec_config

    def get_feature_columns(self):
        return self._feature_column_v1s

    def freeze_slots(self, features):
        assert not self._frozen, "Already finalized"
        if self._config_run:
            raise ConfigRunError()

        self._sparse_v2opt = {}
        bias_config = self._get_bias_slot_configs()
        if bias_config:
            bias_weights = self._bias_embedding.weights
            for i, opt in enumerate(bias_config['optimizers']):
                for j in range(self._num_shards):
                    self._sparse_v2opt[bias_weights[i][j]] = opt

        vec_config = self._get_vec_slot_configs()
        if vec_config:
            vec_weights = self._vec_embedding.weights
            for i, opt in enumerate(vec_config['optimizers']):
                for j in range(self._num_shards):
                    self._sparse_v2opt[vec_weights[i][j]] = opt

            placeholders = []
            dims = []
            for slot_id, _, _, _ in vec_config['slot_list']:
                fc = self._feature_column_v1s[slot_id]
                for sslice in fc.feature_slot.feature_slices:
                    dims.append(sslice.len)
                    placeholders.append(fc.get_vector(sslice))
            vec_split = tf.split(self._vec_tensor, dims, axis=1)
            _swap_tensors(vec_split, placeholders)

        for slot in self._feature_slots.values():
            slot._frozen = True
        self._frozen = True

def _swap_tensor(t0, t1, consumers1):
    nb_update_inputs = 0
    consumers1_indices = {}
    for consumer1 in consumers1:
        consumers1_indices[consumer1] = \
            [i for i, t in enumerate(consumer1.inputs) if t is t1]
    for consumer1 in consumers1:
        for i in consumers1_indices[consumer1]:
            consumer1._update_input(i, t0)  # pylint: disable=protected-access
            nb_update_inputs += 1
    return nb_update_inputs

def _swap_tensors(ts0, ts1):
    """ simple implement for swap ts0, ts1 consumers, like tf v1.x swap_ts"""
    nb_update_inputs = 0
    precomputed_consumers = []
    for t0, t1 in zip(ts0, ts1):
        consumers0 = set(t0.consumers())
        consumers1 = set(t1.consumers())
        precomputed_consumers.append((consumers0, consumers1))
    for t0, t1, consumers in zip(ts0, ts1, precomputed_consumers):
        if t0 is t1:
            continue  # Silently ignore identical tensors.
        consumers0, consumers1 = consumers
        nb_update_inputs += _swap_tensor(t0, t1, consumers1)
        nb_update_inputs += _swap_tensor(t1, t0, consumers0)
    return nb_update_inputs

class SparseFLEstimator(estimator.FLEstimator):
    def __init__(self,
                 cluster_server,
                 trainer_master,
                 bridge,
                 role,
                 model_fn,
                 is_chief=False):
        super(SparseFLEstimator, self).__init__(
            cluster_server, trainer_master, bridge, role, model_fn, is_chief)

        self._bias_slot_configs = None
        self._vec_slot_configs = None
        self._slot_configs = None
        try:
            ps_indices = cluster_server.cluster_spec.task_indices('ps')
        except ValueError:
            ps_indices = None
        finally:
            self._embedding_devices = [None,] if not ps_indices else \
                ['/job:ps/task:%d'%i for i in ps_indices]
        self._num_shards = len(self._embedding_devices)

    def _preprocess_fids(self, fids, configs):
        if fids.indices.shape.rank == 2:
            fids = tf.IndexedSlices(indices=fids.indices[:, 0],
                                    values=fids.values,
                                    dense_shape=fids.dense_shape)
        features = {}
        for config in configs:
            features.update(operator._multidevice_preprocess_fids(
                fids, config, num_shards=self._num_shards))
        return features

    def _set_model_configs(self, mode): #features, labels, mode):
        with tf.Graph().as_default() as g:
            M = SparseFLModel(self._role,
                              self._bridge,
                              None, #features['example_id'],
                              config_run=True)
            try:
                self._model_fn(M, None, None, mode) # features, labels, mode)
            except ConfigRunError as e:
                self._bias_slot_configs = M._get_bias_slot_configs()
                self._vec_slot_configs = M._get_vec_slot_configs()
                self._feature_columns = M.get_feature_columns()
                self._slot_configs = [self._bias_slot_configs,
                                      self._vec_slot_configs]
                return self._slot_configs
        raise UserWarning("Failed to get model config. Did you forget to call \
                           freeze_slots in model_fn?")

    def _get_features_and_labels_from_input_fn(self, input_fn, mode):
        slot_configs = self._set_model_configs(mode) # features, labels, mode)
        def input_fn_wrapper(*args, **kwargs):
            dataset = input_fn(self._bridge, self._trainer_master)
            def mapper(features, *args):
                features.update(self._preprocess_fids(features.pop('fids'),
                                                      slot_configs))
                return (features,) + args if args else features
            dataset = dataset.map(
                mapper, num_parallel_calls=tf.data.experimental.AUTOTUNE)
            return dataset

        return super(SparseFLEstimator, self
            )._get_features_and_labels_from_input_fn(input_fn_wrapper, mode)

    def _get_model_spec(self, features, labels, mode):
        features = features.copy()
        if mode == tf.estimator.ModeKeys.PREDICT:
            fids = tf.IndexedSlices(
                indices=features.pop('fids_indices'),
                values=features.pop('fids_values'),
                dense_shape=features.pop('fids_dense_shape'))
            features.update(self._preprocess_fids(
                fids, self._slot_configs))

        bias_embedding = embedding.Embedding(self._bias_slot_configs,
                                             devices=self._embedding_devices)
        bias_tensor = bias_embedding.lookup(features)
        if self._vec_slot_configs is not None:
            vec_embedding = embedding.Embedding(self._vec_slot_configs,
                                                devices=self._embedding_devices)
            vec_tensor = vec_embedding.lookup(features)
        else:
            vec_embedding = None
            vec_tensor = None

        model = SparseFLModel(self._role, self._bridge,
                              features.get('example_id', None),
                              config_run=False,
                              bias_tensor=bias_tensor,
                              bias_embedding=bias_embedding,
                              vec_tensor=vec_tensor,
                              vec_embedding=vec_embedding,
                              feature_columns=self._feature_columns)

        spec = self._model_fn(model, features, labels, mode)
        assert model._frozen, "Please finalize model in model_fn"
        return spec, model

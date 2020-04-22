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
from . import utils


class FeatureSlice(object):
    """A class to describe a slice of a FeatureSlot.

    Args:
        feature_slot (FeatureSlot): the FeatureSlot this slice belongs to
        begin (int): the start index of this slice
        len (int): the length of this slice
    """
    def __init__(self, feature_slot, begin, length):
        self._feature_slot = feature_slot
        self._begin = begin
        self._end = begin + length

    def __repr__(self):
        return '[FeatureSlice][slot-{}][{}-{}]'.format(
                self._feature_slot.slot_id, self._begin, self._end)

    def __hash__(self):
        return hash((self._feature_slot.slot_id, self._begin, self._end))

    @property
    def begin(self):
        """begin index of the slice"""
        return self._begin

    @property
    def end(self):
        """end index (begin+len) of this slice"""
        return self._end

    @property
    def len(self):
        """length of this slice"""
        return self._end - self._begin


class FeatureSlot(object):
    _default_bias_initializer = None
    _default_vec_initializer = None
    _default_bias_optimizer = None
    _default_vec_optimizer = None

    @staticmethod
    def set_default_bias_initializer(obj):
        FeatureSlot._default_bias_initializer = obj

    @staticmethod
    def set_default_vec_initializer(obj):
        FeatureSlot._default_vec_initializer = obj

    @staticmethod
    def set_default_bias_optimizer(obj):
        FeatureSlot._default_bias_optimizer = obj

    @staticmethod
    def set_default_vec_optimizer(obj):
        FeatureSlot._default_vec_optimizer = obj

    def __init__(self,
                 slot_id,
                 hash_table_size,
                 dtype=None,
                 bias_initializer=None,
                 bias_optimizer=None,
                 vec_initializer=None,
                 vec_optimizer=None):
        assert 0 <= slot_id < utils.MAX_SLOTS, \
            "Invalid slot id %d"%slot_id
        assert dtype is None, "Only support float32 for now"
        self._slot_id = slot_id
        self._hash_table_size = int(hash_table_size)
        self._dtype = tf.float32

        msg = "Please either set {n} or use FeatureSlot.set_default_{n} \
               to set a global default"

        self._bias_initializer = bias_initializer or \
                                 FeatureSlot._default_bias_initializer
        assert self._bias_initializer is not None, \
               msg.format(n='bias_initializer')

        self._bias_optimizer = bias_optimizer or \
                               FeatureSlot._default_bias_optimizer
        assert self._bias_optimizer is not None, \
               msg.format(n='bias_optimizer')

        self._vec_initializer = vec_initializer or \
                                FeatureSlot._default_vec_initializer
        self._vec_optimizer = vec_optimizer or \
                              FeatureSlot._default_vec_optimizer

        self._feature_dim = 0
        self._slices = []
        self._frozen = False

    @property
    def slot_id(self):
        return self._slot_id

    @property
    def hash_table_size(self):
        return self._hash_table_size

    @property
    def dim(self):
        return self._feature_dim + 1

    @property
    def feature_slices(self):
        return self._slices

    def add_slice(self, dim):
        assert not self._frozen, \
            "Cannot modify FeatureSlot after freeze_slots is called"

        msg = "Please either set {n} or use FeatureSlot.set_default_{n} \
               to set a global default"
        assert self._vec_initializer is not None, \
               msg.format(n='vec_initializer')
        assert self._vec_optimizer is not None, msg.format(n='vec_optimizer')

        sslice = FeatureSlice(self, self._feature_dim, dim)
        self._feature_dim += dim
        self._slices.append(sslice)
        return sslice


class FeatureColumnV1(object):
    def __init__(self, feature_slot):
        self._feature_slot = feature_slot
        self._placeholder_slices = {}

    @property
    def feature_slot(self):
        return self._feature_slot

    def get_vector(self, sslice):
        if self._feature_slot is not sslice._feature_slot or \
            sslice not in self._feature_slot._slices:
            raise ValueError('{} is not suitable for this \
                              FeatureColumn'.format(sslice))

        if sslice not in self._placeholder_slices:
            self._placeholder_slices[sslice] = tf.placeholder(
                self._feature_slot._dtype, [None, sslice.len])

        return self._placeholder_slices[sslice]

    def add_vector(self, dim):
        return self.get_vector(self._feature_slot.add_slice(dim))

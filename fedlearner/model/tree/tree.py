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

import os
import math
import queue
import time
import logging
import collections
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from google.protobuf import text_format
import tensorflow.compat.v1 as tf
from fedlearner.model.tree.packing import GradHessPacker
from fedlearner.model.tree.loss import LogisticLoss, MSELoss
from fedlearner.model.crypto import paillier, fixed_point_number
from fedlearner.common import tree_model_pb2 as tree_pb2
from fedlearner.common import common_pb2
from fedlearner.common.metrics import emit_store


BST_TYPE = np.float32
PRECISION = 1e38
EXPONENT = math.floor(
    math.log(PRECISION, fixed_point_number.FixedPointNumber.BASE))
KEY_NBITS = 1024
CIPHER_NBYTES = (KEY_NBITS * 2)//8

MAX_PARTITION_SIZE = 4096


def _send_public_key(bridge, public_key):
    msg = tree_pb2.EncryptedNumbers()
    msg.ciphertext.append(public_key.n.to_bytes(KEY_NBITS//8, 'little'))
    bridge.send_proto('public_key', msg)

def _receive_public_key(bridge):
    msg = tree_pb2.EncryptedNumbers()
    bridge.receive_proto('public_key').Unpack(msg)
    return paillier.PaillierPublicKey(
        int.from_bytes(msg.ciphertext[0], 'little'))

def _encode_encrypted_numbers(numbers):
    return [
        i.ciphertext(False).to_bytes(CIPHER_NBYTES, 'little') \
        for i in numbers]

def _encrypt_numbers(public_key, numbers):
    return _encode_encrypted_numbers(
        [public_key.encrypt(i, PRECISION) for i in numbers])

def _decrypt_number(private_key, numbers):
    return [private_key.decrypt(i) for i in numbers]

def _from_ciphertext(public_key, ciphertext):
    return [
        paillier.PaillierEncryptedNumber(
            public_key, int.from_bytes(i, 'little'), EXPONENT)
        for i in ciphertext]

def _encrypt_and_send_numbers(bridge, name, public_key, numbers):
    num_parts = (len(numbers) + MAX_PARTITION_SIZE - 1)//MAX_PARTITION_SIZE
    bridge.send_proto(
        '%s_partition_info'%name,
        tree_pb2.PartitionInfo(num_partitions=num_parts)
    )
    for i in range(num_parts):
        part = numbers[i*MAX_PARTITION_SIZE:(i+1)*MAX_PARTITION_SIZE]
        msg = tree_pb2.EncryptedNumbers()
        msg.ciphertext.extend(_encrypt_numbers(public_key, part))
        bridge.send_proto('%s_part_%d'%(name, i), msg)

def _raw_encrypt_numbers(args):
    public_key, numbers, part_id = args
    ciphertext = [
        public_key.raw_encrypt(num).to_bytes(CIPHER_NBYTES, 'little')
        for num in numbers
    ]
    return part_id, ciphertext

def _raw_encrypt_and_send_numbers(bridge, name, public_key, numbers, pool=None):
    num_parts = (len(numbers) + MAX_PARTITION_SIZE - 1) // MAX_PARTITION_SIZE
    bridge.send_proto('%s_partition_info' % name,
                      tree_pb2.PartitionInfo(num_partitions=num_parts))
    if not pool:
        for part_id in range(num_parts):
            part = numbers[part_id * MAX_PARTITION_SIZE:
                           (part_id + 1) * MAX_PARTITION_SIZE]
            msg = tree_pb2.EncryptedNumbers()
            part_id, ciphertext = _raw_encrypt_numbers((public_key, part,
                                                        part_id))
            msg.ciphertext.extend(ciphertext)
            bridge.send_proto('%s_part_%d' % (name, part_id), msg)
    else:
        def gen():
            for part_id in range(num_parts):
                part = numbers[part_id * MAX_PARTITION_SIZE:(part_id + 1) *
                               MAX_PARTITION_SIZE]
                yield public_key, part, part_id
        results = pool.map(_raw_encrypt_numbers, gen())
        for res in results:
            part_id, ciphertext = res
            msg = tree_pb2.EncryptedNumbers()
            msg.ciphertext.extend(ciphertext)
            bridge.send_proto('%s_part_%d' % (name, part_id), msg)

def _receive_encrypted_numbers(bridge, name, public_key):
    part_info = tree_pb2.PartitionInfo()
    bridge.receive_proto('%s_partition_info'%name).Unpack(part_info)
    ret = []
    for i in range(part_info.num_partitions):
        msg = tree_pb2.EncryptedNumbers()
        bridge.receive_proto('%s_part_%d'%(name, i)).Unpack(msg)
        ret.extend(_from_ciphertext(public_key, msg.ciphertext))
    return ret

def _get_dtype_for_max_value(max_value):
    if max_value < np.iinfo(np.int8).max:
        return np.int8
    if max_value < np.iinfo(np.int16).max:
        return np.int16
    return np.int32


class BinnedFeatures(object):
    def __init__(self, features, max_bins, cat_features=None):
        super(BinnedFeatures, self).__init__()

        self._max_bins = max_bins
        self.features = features
        self.binned, self.thresholds = self._bin_features(features)
        self.num_bins = [len(i) + 2 for i in self.thresholds]

        if cat_features is None:
            cat_features = np.zeros((features.shape[0], 0), dtype=np.int32)
        self.cat_features = cat_features
        self.cat_num_bins = [
            cat_features[:, i].max()+1 for i in range(cat_features.shape[1])]

        self.num_features = self.features.shape[1]
        self.num_cat_features = self.cat_features.shape[1]
        self.num_all_features = self.num_features + self.num_cat_features

    def _bin_features(self, features):
        thresholds = []
        binned = np.zeros_like(features, dtype=np.uint8, order='F')
        for i in range(features.shape[1]):
            x = features[:, i]
            missing_mask = np.isnan(x)
            nonmissing_x = x
            if missing_mask.any():
                nonmissing_x = x[~missing_mask]
            nonmissing_x = np.ascontiguousarray(
                nonmissing_x, dtype=BST_TYPE)
            unique_x = np.unique(nonmissing_x)
            if len(unique_x) <= self._max_bins:
                threshold = (unique_x[:-1] + unique_x[1:]) * 0.5
            else:
                percentiles = np.linspace(0, 100, num=self._max_bins + 1)
                percentiles = percentiles[1:-1]
                threshold = np.percentile(
                    nonmissing_x, percentiles, interpolation='midpoint')
                assert threshold.size == self._max_bins - 1
            thresholds.append(threshold)

            binned[:, i] = np.searchsorted(threshold, x, side='right')
            binned[missing_mask, i] = threshold.size + 1

        return binned, thresholds


def _compute_histogram_helper(args):
    base, values, binned_features, num_bins, zero = args
    hists = []
    for i, num in enumerate(num_bins):
        logging.debug('Computing histogram for feature %d', base + i)
        hist = np.asarray([zero for _ in range(num)])
        np.add.at(hist, binned_features[:, i], values)
        hists.append(hist)

    return hists


class HistogramBuilder(object):
    def __init__(self, binned_features, dtype=BST_TYPE,
                 num_parallel=1, pool=None):
        self._bins = binned_features
        self._dtype = dtype
        self._zero = dtype(0.0)
        self._num_parallel = num_parallel
        self._pool = pool

    def compute_histogram(self, values, sample_ids):
        if not self._pool:
            hists = _compute_histogram_helper(
                (0, values[sample_ids], self._bins.binned[sample_ids],
                 self._bins.num_bins, self._zero))
            cat_hists = _compute_histogram_helper(
                (self._bins.num_features, values[sample_ids],
                 self._bins.cat_features[sample_ids],
                 self._bins.cat_num_bins, self._zero))
            return hists + cat_hists

        num_jobs = self._num_parallel
        job_size = \
            (self._bins.num_features + num_jobs - 1)//num_jobs
        cat_job_size = \
            (self._bins.num_cat_features + num_jobs - 1)//num_jobs
        args = [
            (job_size*i,
             values[sample_ids],
             self._bins.binned[
                 sample_ids, job_size*i:job_size*(i+1)],
             self._bins.num_bins[job_size*i:job_size*(i+1)],
             self._zero)
            for i in range(self._num_parallel)
        ] + [
            (self._bins.num_features + cat_job_size*i,
             values[sample_ids],
             self._bins.cat_features[
                 sample_ids, cat_job_size*i:cat_job_size*(i+1)],
             self._bins.cat_num_bins[cat_job_size*i:cat_job_size*(i+1)],
             self._zero)
            for i in range(self._num_parallel)
        ]

        rets = self._pool.map(_compute_histogram_helper, args)
        return sum(rets, [])


class GrowerNode(object):
    def __init__(self, node_id):
        self.node_id = node_id
        self.num_features = None
        self.feature_id = None
        self.is_cat_feature = None
        self.threshold = None
        self.cat_threshold = None
        self.default_left = None
        self.is_owner = None
        self.owner_id = None
        self.weight = None

        self.parent = None
        self.left_child = None
        self.right_child = None

        self.sample_ids = []
        self.grad_hists = None
        self.hess_hists = None

        # node impurity and entropy
        self.gini = None
        self.entropy = None

        # information gain and node importance
        self.IG = None
        self.NI = None

    def is_left_sample(self, binned, idx):
        assert self.is_owner

        if self.is_cat_feature:
            x = binned.cat_features[
                idx, self.feature_id - self.num_features]
            return np.in1d(x, self.cat_threshold)

        x = binned.features[idx, self.feature_id]
        isnan = np.isnan(x)
        return np.where(isnan, self.default_left, x < self.threshold)

    def to_proto(self):
        return tree_pb2.RegressionTreeNodeProto(
            node_id=self.node_id,
            left_child=self.left_child,
            right_child=self.right_child,
            parent=self.parent,
            is_owner=self.is_owner,
            owner_id=self.owner_id,
            feature_id=self.feature_id,
            is_cat_feature=self.is_cat_feature,
            threshold=self.threshold,
            cat_threshold=self.cat_threshold,
            default_left=self.default_left,
            weight=self.weight)


class BaseGrower(object):
    def __init__(self, binned, labels, grad, hess,
                 grow_policy='depthwise', max_leaves=None, max_depth=None,
                 learning_rate=0.3, l2_regularization=1.0, dtype=BST_TYPE,
                 num_parallel=1, pool=None):
        self._binned = binned
        self._labels = labels
        self._num_samples = binned.features.shape[0]
        self._is_cat_feature = \
            [False] * binned.num_features + [True] * binned.num_cat_features
        self._grad = grad
        self._hess = hess
        self._grow_policy = grow_policy

        if grow_policy == 'depthwise':
            self._split_candidates = queue.Queue()
            assert max_depth is not None, \
                "max_depth must be set when grow_policy is depthwise"
            self._max_depth = max_depth
            self._max_leaves = 2**max_depth
        else:
            self._split_candidates = queue.PriorityQueue()
            assert max_leaves, \
                "max_leaves must be set when grow_policy is lossguided"
            self._max_leaves = max_leaves
            self._max_depth = max_depth if max_depth is not None else 2**31

        self._learning_rate = learning_rate
        self._l2_regularization = l2_regularization

        self._num_parallel = num_parallel
        self._pool = pool
        assert self._pool or self._num_parallel == 1
        self._hist_builder = HistogramBuilder(
            binned, dtype, num_parallel, self._pool)

        self._nodes = []
        self._add_node(0)
        self._nodes[0].sample_ids = list(range(binned.features.shape[0]))
        self._num_leaves = 1

    def _initialize_feature_importance(self):
        self._feature_importance = np.zeros(len(self._is_cat_feature))

    def _compute_Gini_Entropy(self, node):
        '''
        compute gini and entropy
        '''
        if node.gini is not None:
            return
        node_labels = self._labels[node.sample_ids]
        total = len(node_labels)
        if total == 0:
            node.gini = 0.0
            node.entropy = 0.0
            return
        labels_counter = collections.Counter(node_labels)
        gini = 0.0
        entropy = 0.0
        for _, value in labels_counter.items():
            label_freq = value / total
            if label_freq == 0:
                entropy += 0
            else:
                entropy += -label_freq*math.log(label_freq)
            gini += label_freq*(1-label_freq)
        node.gini = gini
        node.entropy = entropy

    def _compute_IG_NI(self, node, left_child, right_child):
        '''
        compute information gain and node importance
        '''
        #compute node gini and entropy
        self._compute_Gini_Entropy(node)
        self._compute_Gini_Entropy(left_child)
        self._compute_Gini_Entropy(right_child)

        node_len = len(node.sample_ids)
        node_right_len = len(right_child.sample_ids)
        node_left_len = len(left_child.sample_ids)
        if node_len == 0:
            node.IG = 0
            node.NI = 0
            return
        IG = node.entropy - \
            node_left_len / node_len * left_child.entropy - \
            node_right_len / node_len * right_child.entropy

        NI = node_len / self._num_samples * node.gini - \
            node_right_len / self._num_samples * right_child.gini - \
            node_left_len / self._num_samples * left_child.gini
        node.IG = IG
        node.NI = NI

    def _normalize_feature_importance(self):
        if self._feature_importance.sum() != 0.0:

            self._feature_importance = self._feature_importance/ \
                                        self._feature_importance.sum()
            self._feature_importance = self._feature_importance/ \
                                        self._feature_importance.sum()

    def _compute_histogram(self, node):
        node.grad_hists = self._hist_builder.compute_histogram(
            self._grad, node.sample_ids)
        node.hess_hists = self._hist_builder.compute_histogram(
            self._hess, node.sample_ids)

    def _compute_histogram_from_sibling(self, node, sibling):
        parent = self._nodes[node.parent]
        node.grad_hists = [
            p - l for p, l in zip(parent.grad_hists, sibling.grad_hists)]
        node.hess_hists = [
            p - l for p, l in zip(parent.hess_hists, sibling.hess_hists)]

    def _compare_split(self, split_info, default_left,
                       feature_id, split_point,
                       left_g, left_h, right_g, right_h):
        lam = self._l2_regularization
        lr = self._learning_rate
        sum_g = left_g + right_g
        sum_h = left_h + right_h
        gain = left_g*left_g/(left_h + lam) + \
            right_g*right_g/(right_h + lam) - \
            sum_g*sum_g/(sum_h + lam)
        if not gain >= 0:
            logging.warning("the value of gain %f is invalid, left_h: %f, "
                            "right_h: %f, left_g: %f, right_g: %f, lam: %f",
                            gain, left_g, right_g, left_h, right_h, lam)
        if gain > split_info.gain:
            split_info.gain = gain
            split_info.feature_id = feature_id
            split_info.split_point[:] = split_point
            split_info.default_left = default_left
            split_info.left_weight = - lr * left_g/(left_h + lam)
            split_info.right_weight = - lr * right_g/(right_h + lam)

    def _find_split_and_push(self, node):
        assert len(self._is_cat_feature) == len(node.grad_hists)

        split_info = tree_pb2.SplitInfo(
            node_id=node.node_id, gain=-1e38)
        for fid, is_cat in enumerate(self._is_cat_feature):
            if is_cat:
                self._find_cat_split(node, fid, split_info)
            else:
                self._find_cont_split(node, fid, split_info)

        assert len(split_info.split_point) != 0, \
            'the length of split point must not be 0'
        self._split_candidates.put((-split_info.gain, split_info))

        return split_info.gain, split_info

    def _find_cont_split(self, node, fid, split_info):
        grad_hist = node.grad_hists[fid]
        hess_hist = node.hess_hists[fid]
        sum_g = sum(grad_hist)
        sum_h = sum(hess_hist)
        left_g = 0.0
        left_h = 0.0
        nan_g = grad_hist[-1]
        nan_h = hess_hist[-1]
        for i in range(len(grad_hist) - 2):
            left_g += grad_hist[i]
            left_h += hess_hist[i]
            self._compare_split(
                split_info, True, fid, [i],
                left_g + nan_g, left_h + nan_h,
                sum_g - left_g - nan_g, sum_h - left_h - nan_h)
            self._compare_split(
                split_info, False, fid, [i],
                left_g, left_h,
                sum_g - left_g, sum_h - left_h)

    def _find_cat_split(self, node, fid, split_info):
        grad_hist = node.grad_hists[fid]
        hess_hist = node.hess_hists[fid]
        sum_g = sum(grad_hist)
        sum_h = sum(hess_hist)
        left_g = 0.0
        left_h = 0.0
        split_point = []
        order = [
            (i, g/h + self._l2_regularization)
            for i, (g, h) in enumerate(zip(grad_hist, hess_hist))]
        order.sort(key=lambda x: x[1])
        for i, _ in order:
            split_point.append(i)
            left_g += grad_hist[i]
            left_h += hess_hist[i]
            self._compare_split(
                split_info, True, fid, split_point,
                left_g, left_h,
                sum_g - left_g, sum_h)

    def _add_node(self, parent_id):
        node_id = len(self._nodes)
        node = GrowerNode(node_id)
        node.parent = parent_id
        node.num_features = self._binned.num_features
        self._nodes.append(node)
        return node_id

    def _set_node_partition(self, node, split_info):
        node.is_owner = True
        node.feature_id = split_info.feature_id
        if node.feature_id < self._binned.num_features:
            node.is_cat_feature = False
            node.threshold = self._binned.thresholds[
                node.feature_id][split_info.split_point[0]]
        else:
            node.is_cat_feature = True
            node.cat_threshold = split_info.split_point
        node.default_left = split_info.default_left

        left_child = self._nodes[node.left_child]
        right_child = self._nodes[node.right_child]

        is_left = node.is_left_sample(self._binned, node.sample_ids)
        left_child.sample_ids = list(np.asarray(node.sample_ids)[is_left])
        right_child.sample_ids = list(np.asarray(node.sample_ids)[~is_left])

    def _split_next(self):
        _, split_info = self._split_candidates.get()
        node = self._nodes[split_info.node_id]

        node.left_child = self._add_node(node.node_id)
        left_child = self._nodes[node.left_child]
        left_child.weight = split_info.left_weight

        node.right_child = self._add_node(node.node_id)
        right_child = self._nodes[node.right_child]
        right_child.weight = split_info.right_weight

        self._num_leaves += 1

        self._set_node_partition(node, split_info)

        self._compute_IG_NI(node, \
            left_child, right_child)
        self._feature_importance[split_info.feature_id] += node.NI

        return left_child, right_child, split_info

    def _log_split(self, left_child, right_child, split_info):
        parent = self._nodes[split_info.node_id]

        logging.info(
            "Split node %d at feature %d with threshold %s for gain=%f. " \
            "Node gini_impurity=%f, entropy=%f. " \
            "Split information_gain=%f, node_importance=%f." \
            "Left(w=%f, nsamples=%d), Right(w=%f, nsamples=%d). " \
            "nan goes to %s.",
            split_info.node_id, split_info.feature_id,
            split_info.split_point, split_info.gain,
            parent.gini, parent.entropy,
            parent.IG, parent.NI,
            left_child.weight, len(left_child.sample_ids),
            right_child.weight, len(right_child.sample_ids),
            split_info.default_left and 'left' or 'right')
        assert len(left_child.sample_ids) + len(right_child.sample_ids) \
            == len(parent.sample_ids)

    def _log_feature_importance(self):
        logging.info("For current tree, " \
            "feature importance(>0) is %s, " \
            "feature indices(>0) is %s ", \
            self._feature_importance[self._feature_importance > 0], \
            np.nonzero(self._feature_importance))

    def to_proto(self):
        proto = tree_pb2.RegressionTreeProto(
            feature_importance=self._feature_importance)
        for node in self._nodes:
            proto.nodes.append(node.to_proto())
        return proto

    def get_prediction(self):
        prediction = np.zeros(self._binned.features.shape[0], dtype=BST_TYPE)
        for node in self._nodes:
            if node.left_child is not None:
                continue
            prediction[node.sample_ids] = node.weight
        return prediction

    def grow(self):
        self._compute_histogram(self._nodes[0])
        self._initialize_feature_importance()
        self._find_split_and_push(self._nodes[0])

        while self._num_leaves < self._max_leaves:
            left_child, right_child, split_info = self._split_next()
            self._log_split(left_child, right_child, split_info)
            self._compute_histogram(left_child)
            self._find_split_and_push(left_child)
            self._compute_histogram_from_sibling(right_child, left_child)
            self._find_split_and_push(right_child)

        self._normalize_feature_importance()
        self._log_feature_importance()

def _decrypt_histogram_helper(args):
    base, public_key, private_key, hists = args
    rets = []
    for i, hist in enumerate(hists):
        logging.debug('Decrypting histogram for feature %d', base + i)
        hist = _from_ciphertext(public_key, hist.ciphertext)
        rets.append(np.asarray(_decrypt_number(private_key, hist)))
    return rets


def _decrypt_packed_histogram_helper(args):
    base, packer, private_key, hists = args
    grad_hists = []
    hess_hists = []
    for i, hist in enumerate(hists):
        logging.debug('Decrypting packed histogram for feature %d', base + i)
        hist = [int.from_bytes(i, 'little') for i in hist.ciphertext]
        grad_hist, hess_hist = \
            packer.decrypt_and_unpack_grad_hess(hist, private_key)
        grad_hists.append(np.asarray(grad_hist))
        hess_hists.append(np.asarray(hess_hist))
    return grad_hists, hess_hists


class LeaderGrower(BaseGrower):
    def __init__(self, bridge, public_key, private_key,
                 binned, labels, grad, hess, enable_packing=False,
                 **kwargs):
        super(LeaderGrower, self).__init__(
            binned, labels, grad, hess, dtype=np.float32, **kwargs)
        self._bridge = bridge
        self._public_key = public_key
        self._private_key = private_key
        self._enable_packing = enable_packing
        if self._enable_packing:
            self._packer = GradHessPacker(self._public_key, PRECISION, EXPONENT)

        bridge.start()
        follower_num_features, follower_num_cat_features = \
            bridge.receive('feature_dim')
        bridge.commit()
        self._is_cat_feature.extend(
            [False] * follower_num_features + \
            [True] * follower_num_cat_features)

    def _initialize_feature_importance(self):
        self._feature_importance = np.zeros(len(self._nodes[0].grad_hists))

    def _receive_and_decrypt_histogram(self, name):
        msg = tree_pb2.Histograms()
        self._bridge.receive_proto(name).Unpack(msg)
        if not self._pool:
            return _decrypt_histogram_helper(
                (0, self._public_key, self._private_key, msg.hists))

        job_size = (len(msg.hists) + self._num_parallel - 1)//self._num_parallel
        args = [
            (i*job_size,
             self._public_key, self._private_key,
             msg.hists[i*job_size:(i+1)*job_size])
            for i in range(self._num_parallel)
        ]
        hists = self._pool.map(_decrypt_histogram_helper, args)
        return sum(hists, [])

    def _receive_and_decrypt_packed_histogram(self, name):
        msg = tree_pb2.Histograms()
        self._bridge.receive_proto(name).Unpack(msg)
        if not self._pool:
            return _decrypt_packed_histogram_helper(
                (0, self._packer, self._private_key, msg.hists))

        job_size = (len(msg.hists) + self._num_parallel -
                    1) // self._num_parallel
        args = [(i * job_size, self._packer, self._private_key,
                 msg.hists[i * job_size:(i + 1) * job_size])
                for i in range(self._num_parallel)]
        hists = self._pool.map(_decrypt_packed_histogram_helper, args)
        grad_hists = []
        hess_hists = []
        for hist in hists:
            grad_hists.append(hist[0])
            hess_hists.append(hist[1])
        return sum(grad_hists, []), sum(hess_hists, [])

    def _compute_histogram(self, node):
        self._bridge.start()
        grad_hists = self._hist_builder.compute_histogram(
            self._grad, node.sample_ids)
        hess_hists = self._hist_builder.compute_histogram(
            self._hess, node.sample_ids)
        if not self._enable_packing:
            follower_grad_hists = self._receive_and_decrypt_histogram(
                'grad_hists')
            follower_hess_hists = self._receive_and_decrypt_histogram(
                'hess_hists')
        else:
            follower_grad_hists, follower_hess_hists = \
                self._receive_and_decrypt_packed_histogram('gradhess_hists')

        node.grad_hists = grad_hists + follower_grad_hists
        node.hess_hists = hess_hists + follower_hess_hists
        self._bridge.commit()

    def _split_next(self):
        self._bridge.start()

        _, split_info = self._split_candidates.get()
        node = self._nodes[split_info.node_id]

        node.left_child = self._add_node(node.node_id)
        left_child = self._nodes[node.left_child]
        left_child.weight = split_info.left_weight

        node.right_child = self._add_node(node.node_id)
        right_child = self._nodes[node.right_child]
        right_child.weight = split_info.right_weight

        self._num_leaves += 1

        if split_info.feature_id < self._binned.num_all_features:
            self._set_node_partition(node, split_info)
            self._compute_IG_NI(node, \
                left_child, right_child)
            self._feature_importance[split_info.feature_id] += node.NI
            self._bridge.send_proto(
                'split_info',
                tree_pb2.SplitInfo(
                    node_id=split_info.node_id, feature_id=-1,
                    left_samples=left_child.sample_ids,
                    right_samples=right_child.sample_ids))
        else:
            node.is_owner = False
            fid = split_info.feature_id - self._binned.num_all_features
            self._bridge.send_proto(
                'split_info',
                tree_pb2.SplitInfo(
                    node_id=split_info.node_id, feature_id=fid,
                    split_point=split_info.split_point,
                    default_left=split_info.default_left))

            follower_split_info = tree_pb2.SplitInfo()
            self._bridge.receive_proto('follower_split_info') \
                .Unpack(follower_split_info)
            left_child.sample_ids = list(follower_split_info.left_samples)
            right_child.sample_ids = list(follower_split_info.right_samples)

            self._compute_IG_NI(node, \
                left_child, right_child)
            self._feature_importance[split_info.feature_id] += node.NI
            split_info.feature_id = -1


        self._bridge.commit()
        return left_child, right_child, split_info


class FollowerGrower(BaseGrower):
    def __init__(self, bridge, public_key, binned, labels,
                grad, hess, gradhess=None, enable_packing=False,
                 **kwargs):
        dtype = lambda x: public_key.encrypt(x, PRECISION)
        super(FollowerGrower, self).__init__(
            binned, labels, grad, hess, dtype=dtype, **kwargs)
        self._bridge = bridge
        self._public_key = public_key
        self._enable_packing = enable_packing
        self._gradhess = gradhess
        bridge.start()
        bridge.send('feature_dim',
                    [binned.num_features, binned.num_cat_features])
        bridge.commit()

    def _compute_histogram_from_sibling(self, node, sibling):
        pass

    def _normalize_feature_importance(self):
        pass

    def _find_split_and_push(self, node):
        pass

    def _send_histograms(self, name, hists):
        msg = tree_pb2.Histograms()
        for hist in hists:
            ciphertext = _encode_encrypted_numbers(hist)
            msg.hists.append(
                tree_pb2.EncryptedNumbers(ciphertext=ciphertext))
        self._bridge.send_proto(name, msg)

    def _compute_histogram(self, node):
        self._bridge.start()
        if not self._enable_packing:
            grad_hists = self._hist_builder.compute_histogram(
                self._grad, node.sample_ids)
            hess_hists = self._hist_builder.compute_histogram(
                self._hess, node.sample_ids)
            self._send_histograms('grad_hists', grad_hists)
            self._send_histograms('hess_hists', hess_hists)
        else:
            gradhess_hists = self._hist_builder.compute_histogram(
                self._gradhess, node.sample_ids)
            self._send_histograms('gradhess_hists', gradhess_hists)
        self._bridge.commit()

    def _split_next(self):
        self._bridge.start()

        split_info = tree_pb2.SplitInfo()
        self._bridge.receive_proto('split_info').Unpack(split_info)

        node = self._nodes[split_info.node_id]

        node.left_child = self._add_node(node.node_id)
        left_child = self._nodes[node.left_child]
        left_child.weight = float('nan')

        node.right_child = self._add_node(node.node_id)
        right_child = self._nodes[node.right_child]
        right_child.weight = float('nan')

        self._num_leaves += 1

        if split_info.feature_id >= 0:
            self._set_node_partition(node, split_info)
            self._bridge.send_proto(
                'follower_split_info',
                tree_pb2.SplitInfo(
                    left_samples=left_child.sample_ids,
                    right_samples=right_child.sample_ids))
        else:
            node.is_owner = False
            left_child.sample_ids = list(split_info.left_samples)
            right_child.sample_ids = list(split_info.right_samples)

        node.gini = float('nan')
        node.entropy = float('nan')
        node.IG = float('nan')
        node.NI = float('nan')

        self._bridge.commit()
        return left_child, right_child, split_info

def _vectorize_tree(tree):
    vec = {}
    vec['is_owner'] = np.asarray([n.is_owner for n in tree.nodes])
    vec['feature_id'] = np.asarray([n.feature_id for n in tree.nodes])
    vec['is_cat_feature'] = np.asarray([n.is_cat_feature for n in tree.nodes])
    vec['threshold'] = np.asarray([n.threshold for n in tree.nodes])
    vec['cat_threshold'] = [np.asarray(n.cat_threshold) for n in tree.nodes]
    vec['default_left'] = np.asarray(
        [n.default_left for n in tree.nodes], dtype=np.bool)
    vec['is_leaf'] = np.asarray([n.left_child == 0 for n in tree.nodes])
    vec['weight'] = np.asarray([n.weight for n in tree.nodes])
    vec['children'] = np.asarray([
        [n.left_child for n in tree.nodes],
        [n.right_child for n in tree.nodes]])
    return vec

def _vectorized_direction(vec, features, cat_features, assignment):
    fid = vec['feature_id'][assignment]
    is_cont = fid < features.shape[1]

    cont_fid = np.where(is_cont, fid, 0)
    cont_X = features[np.arange(features.shape[0]), cont_fid]
    is_nan = np.isnan(cont_X)
    less = cont_X < vec['threshold'][assignment]
    d = ~np.where(is_nan, vec['default_left'][assignment], less)

    if is_cont.sum() < is_cont.size:
        cond_list = []
        choice_list = []
        is_cat = ~is_cont
        cat_assignment = assignment[is_cat]
        cat_fid = fid[is_cat] - features.shape[1]
        cat_X = cat_features[is_cat, cat_fid]
        for i, cat_threshold in enumerate(vec['cat_threshold']):
            if vec['is_leaf'][i]:
                continue
            cond_list.append(cat_assignment == i)
            choice_list.append(~np.in1d(cat_X, cat_threshold))
        d[is_cat] = np.select(cond_list, choice_list)

    return d

def _vectorized_assignment(vec, assignment, direction, peer_direction=None):
    if peer_direction is not None:
        is_owner = vec['is_owner'][assignment]
        direction = np.where(is_owner, direction, peer_direction)
    new_assignment = vec['children'][direction.astype(np.int32), assignment]
    return np.where(vec['is_leaf'][assignment], assignment, new_assignment)

class BoostingTreeEnsamble(object):
    def __init__(self, bridge, learning_rate=0.3, max_iters=50, max_depth=6,
                 max_leaves=0, l2_regularization=1.0, max_bins=33,
                 grow_policy='depthwise', num_parallel=1,
                 loss_type='logistic', send_scores_to_follower=False,
                 send_metrics_to_follower=False, enable_packing=False):
        self._learning_rate = learning_rate
        self._max_iters = max_iters
        self._max_depth = max_depth
        self._max_leaves = max_leaves
        self._l2_regularization = l2_regularization
        self._grow_policy = grow_policy
        self._num_parallel = num_parallel
        self._pool = None
        if self._num_parallel > 1:
            self._pool = ProcessPoolExecutor(num_parallel)

        assert max_bins < 255, "Only support max_bins < 255"
        self._max_bins = max_bins

        if loss_type == 'logistic':
            self._loss = LogisticLoss()
        elif loss_type == 'mse':
            self._loss = MSELoss()
        else:
            raise ValueError("Invalid loss type%s"%loss_type)
        self._trees = []
        self._feature_names = None
        self._cat_feature_names = None

        self._send_scores_to_follower = send_scores_to_follower
        self._send_metrics_to_follower = send_metrics_to_follower

        self._bridge = bridge
        if bridge is not None:
            self._role = self._bridge.role
            self._bridge.connect()
            self._make_key_pair()
        else:
            self._role = 'local'

        self._enable_packing = enable_packing
        if self._role == 'leader' and self._enable_packing:
            self._packer = GradHessPacker(self._public_key, PRECISION, EXPONENT)

    @property
    def loss(self):
        return self._loss

    def _compute_metrics(self, pred, label):
        if self._role == 'local':
            return self._loss.metrics(pred, label)

        if label is not None:
            metrics = self._loss.metrics(pred, label)
        else:
            metrics = {}

        self._bridge.start()
        if self._role == 'leader':
            if self._send_metrics_to_follower:
                send_metrics = metrics
            else:
                send_metrics = {}

            msg = tf.train.Features()
            for k, v in send_metrics.items():
                msg.feature[k].float_list.value.append(v)
            self._bridge.send_proto('metrics', msg)
        else:
            msg = tf.train.Features()
            self._bridge.receive_proto('metrics').Unpack(msg)
            metrics = {}
            for key in msg.feature:
                metrics[key] = msg.feature[key].float_list.value[0]
        self._bridge.commit()

        return metrics

    def _make_key_pair(self):
        # make key pair
        self._bridge.start()
        if self._role == 'leader':
            self._public_key, self._private_key = \
                paillier.PaillierKeypair.generate_keypair(KEY_NBITS)
            _send_public_key(self._bridge, self._public_key)
        else:
            self._public_key = _receive_public_key(self._bridge)
            self._private_key = None
        self._bridge.commit()

    def _verify_params(self, example_ids, is_training, validation=False,
                       leader_no_data=False):
        assert self._bridge is not None

        self._bridge.start()
        if self._role == 'leader':
            msg = tree_pb2.VerifyParams(
                example_ids=example_ids,
                learning_rate=self._learning_rate,
                max_iters=self._max_iters,
                max_depth=self._max_depth,
                max_leaves=self._max_leaves,
                l2_regularization=self._l2_regularization,
                max_bins=self._max_bins,
                grow_policy=self._grow_policy,
                validation=validation,
                num_trees=len(self._trees),
                leader_no_data=leader_no_data,
                enable_packing=self._enable_packing)
            self._bridge.send_proto('verify', msg)
            status = common_pb2.Status()
            self._bridge.receive_proto('status').Unpack(status)
            assert status.code == common_pb2.STATUS_SUCCESS, \
                "Parameters mismatch between leader and follower: \n%s" \
                %status.error_message
        else:
            msg = tree_pb2.VerifyParams()
            self._bridge.receive_proto('verify').Unpack(msg)
            def check(name, left, right):
                if left == right or \
                        (isinstance(left, float) and np.isclose(left, right)):
                    return ''
                return 'Error:%s mismatch between leader and follower: ' \
                        '%s vs %s\n'%(name, left, right)

            err_msg = ''
            if example_ids and msg.example_ids and \
                    list(example_ids) != list(msg.example_ids):
                err_msg += "Error: example_ids mismatch between leader and " \
                           "follower\n"
                if len(example_ids) != len(msg.example_ids):
                    err_msg += "Error: example_ids length: %d vs %d"%(
                        len(example_ids), len(msg.example_ids))
                else:
                    for i, (a, b) in enumerate(
                                        zip(example_ids, msg.example_ids)):
                        if a != b:
                            err_msg += "Error: first mismatching example at " \
                                       "%d: %s vs %s"%(i, a, b)

            err_msg += check(
                'num_trees', msg.num_trees, len(self._trees))

            if is_training:
                err_msg += check(
                    'learning_rate', msg.learning_rate, self._learning_rate)
                err_msg += check(
                    'max_iters', msg.max_iters, self._max_iters)
                err_msg += check(
                    'max_depth', msg.max_depth, self._max_depth)
                err_msg += check(
                    'max_leaves', msg.max_leaves, self._max_leaves)
                err_msg += check(
                    'l2_regularization', msg.l2_regularization,
                    self._l2_regularization)
                err_msg += check(
                    'max_bins', msg.max_bins, self._max_bins)
                err_msg += check(
                    'grow_policy', msg.grow_policy, self._grow_policy)
                err_msg += check(
                    'validation', msg.validation, validation)
                err_msg += check(
                    'enable_packing', msg.enable_packing, self._enable_packing)

            if err_msg:
                self._bridge.send_proto(
                    'status',
                    common_pb2.Status(
                        code=common_pb2.STATUS_UNKNOWN_ERROR,
                        error_message=err_msg))
                self._bridge.commit()
                raise RuntimeError(err_msg)
            self._bridge.send_proto(
                'status',
                common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS))
        self._bridge.commit()

        return msg

    def save_model(self, path):
        if not tf.io.gfile.exists(os.path.dirname(path)):
            tf.io.gfile.makedirs(os.path.dirname(path))
        fout = tf.io.gfile.GFile(path, 'w')
        model = tree_pb2.BoostingTreeEnsambleProto(
            feature_importance=self._feature_importance,
            feature_names=self._feature_names,
            cat_feature_names=self._cat_feature_names)
        model.trees.extend(self._trees)
        fout.write(text_format.MessageToString(model))

    def load_saved_model(self, path):
        fin = tf.io.gfile.GFile(path, 'r')
        model = tree_pb2.BoostingTreeEnsambleProto()
        text_format.Parse(fin.read(), model,
                          allow_unknown_field=True)
        self._trees = list(model.trees)
        self._feature_importance = np.asarray(model.feature_importance)
        self._feature_names = list(model.feature_names)
        self._cat_feature_names = list(model.cat_feature_names)

    def save_checkpoint(self, path, num_iter):
        filename = os.path.join(
            path,
            'checkpoint-%04d.proto'%num_iter)
        logging.info(
            "Saving checkpoint of iteration %d to %s",
            num_iter, filename)
        self.save_model(filename)
        return filename

    def load_last_checkpoint(self, path):
        files = tf.io.gfile.listdir(path)
        if files:
            last_checkpoint = os.path.join(
                path, sorted(files)[-1])
            logging.info(
                "Restoring from previously saved checkpoint %s", \
                last_checkpoint)
            self.load_saved_model(last_checkpoint)
            return True
        return False

    def batch_score(self, features, labels, example_ids):
        pred = self.batch_predict(features, example_ids=example_ids)
        return self._compute_metrics(pred, labels)

    def batch_predict(self, features, cat_features=None,
                      get_raw_score=False, example_ids=None,
                      feature_names=None, cat_feature_names=None):
        if feature_names and self._feature_names:
            assert feature_names == self._feature_names, \
                "Predict data's feature names does not match loaded model"
        if cat_feature_names and self._cat_feature_names:
            assert cat_feature_names == self._cat_feature_names, \
                "Predict data's feature names does not match loaded model"

        if features is not None and cat_features is None:
            cat_features = np.zeros((features.shape[0], 0), dtype=np.int32)

        if self._bridge is None:
            return self._batch_predict_local(
                features, cat_features, get_raw_score)

        if self._role == 'leader':
            leader_no_data = True
            for tree in self._trees:
                for node in tree.nodes:
                    if node.is_owner:
                        leader_no_data = False
        else:
            leader_no_data = False

        msg = self._verify_params(
            example_ids, False,
            leader_no_data=leader_no_data)

        if msg.leader_no_data:
            if self._role == 'leader':
                return self._batch_predict_one_side_leader(
                    get_raw_score)
            return self._batch_predict_one_side_follower(
                features, cat_features, get_raw_score)

        return self._batch_predict_two_side(
            features, cat_features, get_raw_score)


    def _batch_predict_local(self, features, cat_features, get_raw_score):
        N = features.shape[0]

        raw_prediction = np.zeros(N, dtype=BST_TYPE)
        for idx, tree in enumerate(self._trees):
            logging.debug("Running prediction for tree %d", idx)

            vec_tree = _vectorize_tree(tree)
            assignment = np.zeros(N, dtype=np.int32)
            while vec_tree['is_leaf'][assignment].sum() < N:
                direction = _vectorized_direction(
                    vec_tree, features, cat_features, assignment)
                assignment = _vectorized_assignment(
                    vec_tree, assignment, direction)

            raw_prediction += vec_tree['weight'][assignment]

        if get_raw_score:
            return raw_prediction
        return self._loss.predict(raw_prediction)

    def _batch_predict_one_side_follower(self, features, cat_features,
                                         get_raw_score):
        N = features.shape[0]

        for idx, tree in enumerate(self._trees):
            logging.debug("Running prediction for tree %d", idx)

            vec_tree = _vectorize_tree(tree)
            assignment = np.zeros(
                N, dtype=_get_dtype_for_max_value(len(tree.nodes)))
            while vec_tree['is_leaf'][assignment].sum() < N:
                direction = _vectorized_direction(
                    vec_tree, features, cat_features, assignment)
                assignment = _vectorized_assignment(
                    vec_tree, assignment, direction)

            self._bridge.start()
            self._bridge.send(
                'follower_assignment_%d'%idx,
                assignment)
            self._bridge.commit()

        self._bridge.start()
        raw_prediction = self._bridge.receive('raw_prediction')
        self._bridge.commit()

        if get_raw_score:
            return raw_prediction
        return self._loss.predict(raw_prediction)

    def _batch_predict_one_side_leader(self, get_raw_score):
        raw_prediction = None
        for idx, tree in enumerate(self._trees):
            logging.debug("Running prediction for tree %d", idx)
            vec_tree = _vectorize_tree(tree)
            assert not vec_tree['is_owner'].sum(), \
                "Model cannot predict with no data"

            self._bridge.start()
            assignment = self._bridge.receive('follower_assignment_%d'%idx)
            self._bridge.commit()

            if raw_prediction is None:
                raw_prediction = np.zeros(assignment.shape[0], dtype=BST_TYPE)
            raw_prediction += vec_tree['weight'][assignment]

        self._bridge.start()
        self._bridge.send(
            'raw_prediction',
            raw_prediction*self._send_scores_to_follower)
        self._bridge.commit()

        if get_raw_score:
            return raw_prediction
        return self._loss.predict(raw_prediction)


    def _batch_predict_two_side(self, features, cat_features, get_raw_score):
        N = features.shape[0]
        peer_role = 'leader' if self._role == 'follower' else 'follower'
        raw_prediction = np.zeros(N, dtype=BST_TYPE)
        for idx, tree in enumerate(self._trees):
            logging.debug("Running prediction for tree %d", idx)
            vec_tree = _vectorize_tree(tree)
            assignment = np.zeros(N, dtype=np.int32)
            while vec_tree['is_leaf'][assignment].sum() < N:
                direction = _vectorized_direction(
                    vec_tree, features, cat_features, assignment)

                self._bridge.start()
                self._bridge.send(
                    '%s_direction_%d'%(self._role, idx),
                    direction)
                peer_direction = self._bridge.receive(
                    '%s_direction_%d'%(peer_role, idx))
                self._bridge.commit()

                assignment = _vectorized_assignment(
                    vec_tree, assignment, direction, peer_direction)

            raw_prediction += vec_tree['weight'][assignment]

        self._bridge.start()
        if self._role == 'leader':
            self._bridge.send(
                'raw_prediction',
                raw_prediction*self._send_scores_to_follower)
        else:
            raw_prediction = self._bridge.receive('raw_prediction')
        self._bridge.commit()

        if get_raw_score:
            return raw_prediction
        return self._loss.predict(raw_prediction)

    def _write_training_log(self, filename, header, metrics, pred):
        if not tf.io.gfile.exists(os.path.dirname(filename)):
            tf.io.gfile.makedirs(os.path.dirname(filename))
        if not tf.io.gfile.exists(filename):
            fout = tf.io.gfile.GFile(filename, 'w')
        else:
            fout = tf.io.gfile.GFile(filename, 'a')
        fout.write(header + '\n')
        fout.write(str(metrics) + '\n')
        fout.write(','.join([str(i) for i in pred]) + '\n')
        fout.close()

    def iter_metrics_handler(self, metrics, mode):
        for name, value in metrics.items():
            emit_store(name=name, value=value,
                       tags={'iteration': len(self._trees), 'mode': mode})

    def fit(self,
            features,
            labels=None,
            cat_features=None,
            example_ids=None,
            validation_features=None,
            validation_labels=None,
            validation_cat_features=None,
            validation_example_ids=None,
            feature_names=None,
            cat_feature_names=None,
            checkpoint_path=None,
            output_path=None):
        num_examples = features.shape[0]
        assert example_ids is None or num_examples == len(example_ids)

        # sort feature columns
        binned = BinnedFeatures(
            features, self._max_bins, cat_features=cat_features)

        # load checkpoint if exists
        if checkpoint_path:
            tf.io.gfile.makedirs(checkpoint_path)
            logging.info("Checkpointing into path %s...", checkpoint_path)
            self.load_last_checkpoint(checkpoint_path)

        # verify parameters
        if self._bridge is not None:
            self._verify_params(
                example_ids, True, validation_features is not None)

        # initial f(x)
        if len(self._trees) > 0:
            # feature importance already loaded
            if feature_names and self._feature_names:
                assert feature_names == self._feature_names, \
                    "Training data's feature does not match loaded model"
            if cat_feature_names and self._cat_feature_names:
                assert cat_feature_names == self._cat_feature_names, \
                    "Training data's feature does not match loaded model"
            sum_prediction = self.batch_predict(features, get_raw_score=True)
        else:
            self._feature_names = feature_names
            self._cat_feature_names = cat_feature_names
            sum_prediction = np.zeros(num_examples, dtype=BST_TYPE)

        # start iterations
        while len(self._trees) < self._max_iters:
            begin_time = time.time()
            num_iter = len(self._trees)

            # grow tree
            if self._bridge is None:
                tree, raw_prediction = self._fit_one_round_local(
                    sum_prediction, binned, labels)
                sum_prediction += raw_prediction
            elif self._role == 'leader':
                tree, raw_prediction = self._fit_one_round_leader(
                    sum_prediction, binned, labels)
                sum_prediction += raw_prediction
            else:
                tree = self._fit_one_round_follower(binned)
            self._trees.append(tree)

            logging.info("Elapsed time for one round %s s",
                         str(time.time()-begin_time))

            if num_iter == 0:
                #initialize feature importance for round 0
                self._feature_importance = np.asarray(tree.feature_importance)
            else:
                # update feature_importance
                self._feature_importance = (self._feature_importance*num_iter+ \
                    np.asarray(tree.feature_importance))/len(self._trees)

            logging.info(
                "ensemble feature importance for round %d, " \
                "feature importance(>0) is %s, " \
                "feature indices(>0) is %s ", \
                num_iter, \
                self._feature_importance[self._feature_importance > 0], \
                np.nonzero(self._feature_importance))

            # save check point
            if checkpoint_path is not None:
                self.save_checkpoint(checkpoint_path, num_iter)

            # save output
            pred = self._loss.predict(sum_prediction)
            if labels is not None:
                metrics = self._loss.metrics(pred, labels)
            else:
                metrics = {}
            if output_path is not None:
                self._write_training_log(
                    output_path, 'train_%d'%num_iter, metrics, pred)
            self.iter_metrics_handler(metrics, mode='train')

            # validation
            if validation_features is not None:
                val_pred = self.batch_predict(
                    validation_features,
                    example_ids=validation_example_ids,
                    cat_features=validation_cat_features)
                metrics = self._compute_metrics(val_pred, validation_labels)
                self.iter_metrics_handler(metrics, mode='eval')

                logging.info(
                    "Validation metrics for iter %d: %s", num_iter, metrics)
                if output_path is not None:
                    self._write_training_log(
                        output_path, 'val_%d'%num_iter, metrics, val_pred)

        return self._loss.predict(sum_prediction)


    def _fit_one_round_local(self, sum_fx, binned, labels):
        # compute grad and hess
        pred = self._loss.predict(sum_fx)
        grad = self._loss.gradient(sum_fx, pred, labels)
        hess = self._loss.hessian(sum_fx, pred, labels)
        logging.info(
            'Leader starting iteration %d. Metrics are %s',
            len(self._trees), self._compute_metrics(pred, labels))

        grower = BaseGrower(
            binned, labels, grad, hess,
            learning_rate=self._learning_rate,
            max_depth=self._max_depth,
            max_leaves=self._max_leaves,
            l2_regularization=self._l2_regularization,
            grow_policy=self._grow_policy,
            num_parallel=self._num_parallel,
            pool=self._pool)
        grower.grow()

        return grower.to_proto(), grower.get_prediction()

    def _fit_one_round_leader(self, sum_fx, binned, labels):
        # compute grad and hess
        pred = self._loss.predict(sum_fx)
        grad = self._loss.gradient(sum_fx, pred, labels)
        hess = self._loss.hessian(sum_fx, pred, labels)
        logging.info(
            'Training metrics at start of iteration %d: %s',
            len(self._trees), self._compute_metrics(pred, labels))

        self._bridge.start()
        if not self._enable_packing:
            _encrypt_and_send_numbers(self._bridge, 'grad', self._public_key,
                                      grad)
            _encrypt_and_send_numbers(self._bridge, 'hess', self._public_key,
                                      hess)
        else:
            gradhess_plaintest = self._packer.pack_grad_hess(grad, hess)
            _raw_encrypt_and_send_numbers(self._bridge, 'gradhess',
                                          self._public_key, gradhess_plaintest,
                                          self._pool)
        self._bridge.commit()

        grower = LeaderGrower(
            self._bridge, self._public_key, self._private_key,
            binned, labels, grad, hess,
            enable_packing=self._enable_packing,
            learning_rate=self._learning_rate,
            max_depth=self._max_depth,
            max_leaves=self._max_leaves,
            l2_regularization=self._l2_regularization,
            grow_policy=self._grow_policy,
            num_parallel=self._num_parallel,
            pool=self._pool)
        grower.grow()

        return grower.to_proto(), grower.get_prediction()


    def _fit_one_round_follower(self, binned):
        logging.info(
            'Training metrics at start of iteration %d: %s',
            len(self._trees), self._compute_metrics(None, None))
        # compute grad and hess
        self._bridge.start()
        if not self._enable_packing:
            grad = np.asarray(
                _receive_encrypted_numbers(self._bridge, 'grad',
                                           self._public_key))
            assert len(grad) == binned.features.shape[0]
            hess = np.asarray(
                _receive_encrypted_numbers(self._bridge, 'hess',
                                           self._public_key))
            assert len(hess) == binned.features.shape[0]
            gradhess = None
        else:
            grad = None
            hess = None
            gradhess = np.asarray(
                _receive_encrypted_numbers(self._bridge, 'gradhess',
                                           self._public_key))
        self._bridge.commit()
        logging.info(
            'Follower starting iteration %d.',
            len(self._trees))

        # labels is None for follower
        grower = FollowerGrower(
            self._bridge, self._public_key,
            binned, None, grad, hess, gradhess,
            enable_packing=self._enable_packing,
            learning_rate=self._learning_rate,
            max_depth=self._max_depth,
            max_leaves=self._max_leaves,
            l2_regularization=self._l2_regularization,
            grow_policy=self._grow_policy,
            num_parallel=self._num_parallel,
            pool=self._pool)
        grower.grow()

        return grower.to_proto()

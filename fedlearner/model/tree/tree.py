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
import multiprocessing as mp
import numpy as np
from google.protobuf import text_format

import tensorflow.compat.v1 as tf

from fedlearner.model.tree.loss import LogisticLoss
from fedlearner.model.crypto import paillier, fixed_point_number
from fedlearner.common import tree_model_pb2 as tree_pb2
from fedlearner.common import common_pb2


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
    bridge.send_proto(bridge.current_iter_id, 'public_key', msg)

def _receive_public_key(bridge):
    msg = tree_pb2.EncryptedNumbers()
    bridge.receive_proto(bridge.current_iter_id, 'public_key').Unpack(msg)
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
        bridge.current_iter_id, '%s_partition_info'%name,
        tree_pb2.PartitionInfo(num_partitions=num_parts)
    )
    for i in range(num_parts):
        part = numbers[i*MAX_PARTITION_SIZE:(i+1)*MAX_PARTITION_SIZE]
        msg = tree_pb2.EncryptedNumbers()
        msg.ciphertext.extend(_encrypt_numbers(public_key, part))
        bridge.send_proto(
            bridge.current_iter_id, '%s_part_%d'%(name, i), msg)

def _receive_encrypted_numbers(bridge, name, public_key):
    part_info = tree_pb2.PartitionInfo()
    bridge.receive_proto(
        bridge.current_iter_id, '%s_partition_info'%name).Unpack(part_info)
    ret = []
    for i in range(part_info.num_partitions):
        msg = tree_pb2.EncryptedNumbers()
        bridge.receive_proto(
            bridge.current_iter_id, '%s_part_%d'%(name, i)).Unpack(msg)
        ret.extend(_from_ciphertext(public_key, msg.ciphertext))
    return ret

class BinnedFeatures(object):
    def __init__(self, features, max_bins):
        super(BinnedFeatures, self).__init__()

        self._max_bins = max_bins
        self.features = features
        self.binned, self.thresholds = self._bin_features(features)

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
    base, values, binned_features, thresholds, zero = args
    hists = []
    for i, threshold in enumerate(thresholds):
        logging.debug('Computing histogram for feature %d', base + i)
        num_bins = threshold.size + 2
        hist = np.asarray([zero for _ in range(num_bins)])
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
        if self._num_parallel > 1:
            assert pool is not None
            self._job_size = \
                (len(self._bins.binned[0]) + num_parallel - 1)//num_parallel

    def compute_histogram(self, values, sample_ids):
        if not self._pool:
            return _compute_histogram_helper(
                (0, values[sample_ids], self._bins.binned[sample_ids],
                 self._bins.thresholds, self._zero))

        args = [
            (self._job_size*i,
             values[sample_ids],
             self._bins.binned[
                 sample_ids, self._job_size*i:self._job_size*(i+1)],
             self._bins.thresholds[self._job_size*i:self._job_size*(i+1)],
             self._zero)
            for i in range(self._num_parallel)
        ]

        rets = self._pool.map(_compute_histogram_helper, args)
        return sum(rets, [])


class GrowerNode(object):
    def __init__(self, node_id):
        self.node_id = node_id
        self.feature_id = None
        self.threshold = None
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

    def is_left_sample(self, x):
        assert self.is_owner

        if np.isnan(x):
            if self.default_left:
                return True
            return False

        if x < self.threshold:
            return True
        return False

    def to_proto(self):
        return tree_pb2.RegressionTreeNodeProto(
            node_id=self.node_id,
            left_child=self.left_child,
            right_child=self.right_child,
            parent=self.parent,
            is_owner=self.is_owner,
            owner_id=self.owner_id,
            feature_id=self.feature_id,
            threshold=self.threshold,
            default_left=self.default_left,
            weight=self.weight)


class BaseGrower(object):
    def __init__(self, binned, grad, hess, grow_policy='depthwise',
                 max_leaves=None, max_depth=None, learning_rate=0.3,
                 l2_regularization=1.0, dtype=BST_TYPE,
                 num_parallel=1, pool=None):
        self._binned = binned
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

        self._nodes = [GrowerNode(0)]
        self._nodes[0].sample_ids = list(range(binned.features.shape[0]))
        self._num_leaves = 1

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
        if gain > split_info.gain:
            split_info.gain = gain
            split_info.feature_id = feature_id
            split_info.split_point = split_point
            split_info.default_left = default_left
            split_info.left_weight = - lr * left_g/(left_h + lam)
            split_info.right_weight = - lr * right_g/(right_h + lam)

    def _find_split_and_push(self, node):
        split_info = tree_pb2.SplitInfo(
            node_id=node.node_id, gain=-1)
        for fid, (grad_hist, hess_hist) in \
                enumerate(zip(node.grad_hists, node.hess_hists)):
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
                    split_info, True, fid, i,
                    left_g + nan_g, left_h + nan_h,
                    sum_g - left_g - nan_g, sum_h - left_h - nan_h)
                self._compare_split(
                    split_info, False, fid, i,
                    left_g, left_h,
                    sum_g - left_g, sum_h - left_h)

        self._split_candidates.put((-split_info.gain, split_info))

        return split_info.gain, split_info

    def _add_node(self, parent_id):
        node_id = len(self._nodes)
        node = GrowerNode(node_id)
        node.parent = parent_id
        self._nodes.append(node)
        return node_id

    def _set_node_partition(self, node, split_info):
        node.is_owner = True
        node.feature_id = split_info.feature_id
        node.threshold = self._binned.thresholds[
            split_info.feature_id][split_info.split_point]
        node.default_left = split_info.default_left

        left_child = self._nodes[node.left_child]
        right_child = self._nodes[node.right_child]

        for i in node.sample_ids:
            if node.is_left_sample(self._binned.features[i, node.feature_id]):
                left_child.sample_ids.append(i)
            else:
                right_child.sample_ids.append(i)

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

        return left_child, right_child, split_info

    def _log_split(self, left_child, right_child, split_info):
        parent = self._nodes[split_info.node_id]

        logging.info(
            "Split node %d at feature %d for gain=%f. " \
            "Left(w=%f, nsamples=%d), Right(w=%f, nsamples=%d). " \
            "nan goes to %s.",
            split_info.node_id, split_info.feature_id, split_info.gain,
            left_child.weight, len(left_child.sample_ids),
            right_child.weight, len(right_child.sample_ids),
            split_info.default_left and 'left' or 'right')
        assert len(left_child.sample_ids) + len(right_child.sample_ids) \
            == len(parent.sample_ids)

    def to_proto(self):
        proto = tree_pb2.RegressionTreeProto()
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
        self._find_split_and_push(self._nodes[0])

        while self._num_leaves < self._max_leaves:
            left_child, right_child, split_info = self._split_next()
            self._log_split(left_child, right_child, split_info)
            self._compute_histogram(left_child)
            self._find_split_and_push(left_child)
            self._compute_histogram_from_sibling(right_child, left_child)
            self._find_split_and_push(right_child)

def _decrypt_histogram_helper(args):
    base, public_key, private_key, hists = args
    rets = []
    for i, hist in enumerate(hists):
        logging.debug('Decrypting histogram for feature %d', base + i)
        hist = _from_ciphertext(public_key, hist.ciphertext)
        rets.append(np.asarray(_decrypt_number(private_key, hist)))
    return rets

class LeaderGrower(BaseGrower):
    def __init__(self, bridge, public_key, private_key,
                 binned, grad, hess, **kwargs):
        super(LeaderGrower, self).__init__(
            binned, grad, hess, dtype=np.float32, **kwargs)
        self._bridge = bridge
        self._public_key = public_key
        self._private_key = private_key

    def _receive_and_decrypt_histogram(self, name):
        msg = tree_pb2.Histograms()
        self._bridge.receive_proto(
            self._bridge.current_iter_id, name).Unpack(msg)
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

    def _compute_histogram(self, node):
        self._bridge.start(self._bridge.new_iter_id())
        grad_hists = self._hist_builder.compute_histogram(
            self._grad, node.sample_ids)
        hess_hists = self._hist_builder.compute_histogram(
            self._hess, node.sample_ids)
        follower_grad_hists = self._receive_and_decrypt_histogram('grad_hists')
        follower_hess_hists = self._receive_and_decrypt_histogram('hess_hists')
        node.grad_hists = grad_hists + follower_grad_hists
        node.hess_hists = hess_hists + follower_hess_hists
        self._bridge.commit()

    def _split_next(self):
        self._bridge.start(self._bridge.new_iter_id())

        _, split_info = self._split_candidates.get()
        node = self._nodes[split_info.node_id]

        node.left_child = self._add_node(node.node_id)
        left_child = self._nodes[node.left_child]
        left_child.weight = split_info.left_weight

        node.right_child = self._add_node(node.node_id)
        right_child = self._nodes[node.right_child]
        right_child.weight = split_info.right_weight

        self._num_leaves += 1

        if split_info.feature_id < self._binned.features.shape[1]:
            self._set_node_partition(node, split_info)
            self._bridge.send_proto(
                self._bridge.current_iter_id, 'split_info',
                tree_pb2.SplitInfo(
                    node_id=split_info.node_id, feature_id=-1,
                    left_samples=left_child.sample_ids,
                    right_samples=right_child.sample_ids))
        else:
            node.is_owner = False
            fid = split_info.feature_id - self._binned.features.shape[1]
            self._bridge.send_proto(
                self._bridge.current_iter_id, 'split_info',
                tree_pb2.SplitInfo(
                    node_id=split_info.node_id, feature_id=fid,
                    split_point=split_info.split_point,
                    default_left=split_info.default_left))

            split_info.feature_id = -1
            follower_split_info = tree_pb2.SplitInfo()
            self._bridge.receive_proto(
                self._bridge.current_iter_id, 'follower_split_info') \
                .Unpack(follower_split_info)
            left_child.sample_ids = list(follower_split_info.left_samples)
            right_child.sample_ids = list(follower_split_info.right_samples)

        self._bridge.commit()
        return left_child, right_child, split_info


class FollowerGrower(BaseGrower):
    def __init__(self, bridge, public_key, binned, grad, hess, **kwargs):
        dtype = lambda x: public_key.encrypt(x, PRECISION)
        super(FollowerGrower, self).__init__(
            binned, grad, hess, dtype=dtype, **kwargs)
        self._bridge = bridge
        self._public_key = public_key

    def _compute_histogram_from_sibling(self, node, sibling):
        pass

    def _find_split_and_push(self, node):
        pass

    def _send_histograms(self, name, hists):
        msg = tree_pb2.Histograms()
        for hist in hists:
            ciphertext = _encode_encrypted_numbers(hist)
            msg.hists.append(
                tree_pb2.EncryptedNumbers(ciphertext=ciphertext))
        self._bridge.send_proto(self._bridge.current_iter_id, name, msg)

    def _compute_histogram(self, node):
        self._bridge.start(self._bridge.new_iter_id())
        grad_hists = self._hist_builder.compute_histogram(
            self._grad, node.sample_ids)
        hess_hists = self._hist_builder.compute_histogram(
            self._hess, node.sample_ids)
        self._send_histograms('grad_hists', grad_hists)
        self._send_histograms('hess_hists', hess_hists)
        self._bridge.commit()

    def _split_next(self):
        self._bridge.start(self._bridge.new_iter_id())

        split_info = tree_pb2.SplitInfo()
        self._bridge.receive_proto(
            self._bridge.current_iter_id, 'split_info') \
            .Unpack(split_info)

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
                self._bridge.current_iter_id, 'follower_split_info',
                tree_pb2.SplitInfo(
                    left_samples=left_child.sample_ids,
                    right_samples=right_child.sample_ids))
        else:
            node.is_owner = False
            left_child.sample_ids = list(split_info.left_samples)
            right_child.sample_ids = list(split_info.right_samples)

        self._bridge.commit()
        return left_child, right_child, split_info

def _node_test_feature(node, features, i):
    if not node.is_owner:
        return -1

    x = features[i, node.feature_id]
    if np.isnan(x):
        if node.default_left:
            return node.left_child
        return node.right_child

    if x < node.threshold:
        return node.left_child
    return node.right_child

class BoostingTreeEnsamble(object):
    def __init__(self, bridge, learning_rate=0.3, max_iters=50, max_depth=6,
                 max_leaves=0, l2_regularization=1.0, max_bins=33,
                 grow_policy='depthwise', num_parallel=1):
        self._learning_rate = learning_rate
        self._max_iters = max_iters
        self._max_depth = max_depth
        self._max_leaves = max_leaves
        self._l2_regularization = l2_regularization
        self._grow_policy = grow_policy
        self._num_parallel = num_parallel
        self._pool = None
        if self._num_parallel > 1:
            self._pool = mp.Pool(num_parallel)

        assert max_bins < 255, "Only support max_bins < 255"
        self._max_bins = max_bins

        self._loss = LogisticLoss()
        self._trees = []

        self._bridge = bridge
        if bridge is not None:
            self._role = self._bridge.role
            self._bridge.connect()
            self._make_key_pair()
        else:
            self._role = 'local'

    @property
    def loss(self):
        return self._loss

    def _make_key_pair(self):
        # make key pair
        self._bridge.start(self._bridge.new_iter_id())
        if self._role == 'leader':
            self._public_key, self._private_key = \
                paillier.PaillierKeypair.generate_keypair(KEY_NBITS)
            _send_public_key(self._bridge, self._public_key)
        else:
            self._public_key = _receive_public_key(self._bridge)
            self._private_key = None
        self._bridge.commit()

    def _verify_params(self, example_ids, is_training, validation=False):
        if self._bridge is None:
            return

        self._bridge.start(self._bridge.new_iter_id())
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
                validation=validation)
            self._bridge.send_proto(
                self._bridge.current_iter_id, 'verify', msg)
            status = common_pb2.Status()
            self._bridge.receive_proto(
                self._bridge.current_iter_id, 'status').Unpack(status)
            assert status.code == common_pb2.STATUS_SUCCESS, \
                "Parameters mismatch between leader and follower: \n%s" \
                %status.error_message
        else:
            msg = tree_pb2.VerifyParams()
            self._bridge.receive_proto(
                self._bridge.current_iter_id, 'verify').Unpack(msg)
            def check(name, left, right):
                if left == right or \
                        (isinstance(left, float) and np.isclose(left, right)):
                    return ''
                return 'Error:%s mismatch between leader and follower: ' \
                        '%s vs %s\n'%(name, left, right)

            err_msg = ''
            if example_ids and msg.example_ids and \
                    list(example_ids) != list(msg.example_ids):
                err_msg += "example_ids mismatch between leader and follower"
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

            if err_msg:
                self._bridge.send_proto(
                    self._bridge.current_iter_id, 'status',
                    common_pb2.Status(
                        code=common_pb2.STATUS_UNKNOWN_ERROR,
                        error_message=err_msg))
                raise RuntimeError(err_msg)
            self._bridge.send_proto(
                self._bridge.current_iter_id, 'status',
                common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS))
        self._bridge.commit()


    def save_model(self, path):
        fout = tf.io.gfile.GFile(path, 'w')
        model = tree_pb2.BoostingTreeEnsambleProto()
        model.trees.extend(self._trees)
        fout.write(text_format.MessageToString(model))

    def load_saved_model(self, path):
        fin = tf.io.gfile.GFile(path, 'r')
        model = tree_pb2.BoostingTreeEnsambleProto()
        text_format.Parse(fin.read(), model)
        self._trees = list(model.trees)

    def batch_score(self, features, labels, example_ids):
        pred = self.batch_predict(features, example_ids=example_ids)
        return self._loss.metrics(pred, labels)

    def batch_predict(self, features, get_raw_score=False, example_ids=None):
        if self._bridge is None:
            return self._batch_predict_local(features, get_raw_score)

        self._verify_params(example_ids, False)
        if self._role == 'leader':
            return self._batch_predict_leader(features, get_raw_score)
        return self._batch_predict_follower(features, get_raw_score)


    def _batch_predict_local(self, features, get_raw_score):
        N = features.shape[0]
        raw_prediction = []
        for i in range(features.shape[0]):
            score = 0.0
            for tree in self._trees:
                node = tree.nodes[0]
                while node.left_child != 0:
                    assert node.is_owner
                    new_node_id = _node_test_feature(node, features, i)
                    node = tree.nodes[new_node_id]
                score += node.weight
            raw_prediction.append(score)
        raw_prediction = np.asarray(raw_prediction)
        if get_raw_score:
            return raw_prediction
        return self._loss.predict(raw_prediction)

    def _batch_predict_leader(self, features, get_raw_score):
        N = features.shape[0]
        raw_prediction = np.zeros(N, dtype=BST_TYPE)
        for tree in self._trees:
            assignment = np.zeros(N, dtype=np.int32)
            finish_count = 0
            while finish_count != N:
                self._bridge.start(self._bridge.new_iter_id())
                finish_count = 0
                for i in range(N):
                    node = tree.nodes[assignment[i]]
                    if node.left_child == 0:
                        finish_count += 1
                        continue
                    assignment[i] = _node_test_feature(node, features, i)

                self._bridge.send(
                    self._bridge.current_iter_id, 'leader_assignment',
                    assignment)
                follower_assignment = self._bridge.receive(
                    self._bridge.current_iter_id, 'follower_assignment')
                assignment = np.maximum(assignment, follower_assignment)
                self._bridge.commit()
            for i in range(N):
                raw_prediction[i] += tree.nodes[assignment[i]].weight

        if get_raw_score:
            return raw_prediction
        return self._loss.predict(raw_prediction)

    def _batch_predict_follower(self, features, get_raw_score):
        N = features.shape[0]
        for tree in self._trees:
            assignment = np.zeros(N, dtype=np.int32)
            finish_count = 0
            while finish_count != N:
                self._bridge.start(self._bridge.new_iter_id())
                finish_count = 0
                for i in range(N):
                    node = tree.nodes[assignment[i]]
                    if node.left_child == 0:
                        finish_count += 1
                        continue
                    assignment[i] = _node_test_feature(node, features, i)

                self._bridge.send(
                    self._bridge.current_iter_id, 'follower_assignment',
                    assignment)
                leader_assignment = self._bridge.receive(
                    self._bridge.current_iter_id, 'leader_assignment')
                assignment = np.maximum(assignment, leader_assignment)
                self._bridge.commit()
        return np.zeros(N, dtype=BST_TYPE)

    def _write_training_log(self, filename, header, metrics, pred):
        fout = tf.io.gfile.GFile(filename, 'a')
        fout.write(header + '\n')
        fout.write(str(metrics) + '\n')
        fout.write(','.join([str(i) for i in pred]) + '\n')
        fout.close()

    def fit(self, features, labels=None,
            checkpoint_path=None, example_ids=None,
            validation_features=None, validation_labels=None,
            validation_example_ids=None,
            output_path=None):
        num_examples = features.shape[0]
        assert example_ids is None or num_examples == len(example_ids)

        # verify parameters
        self._verify_params(
            example_ids, True, validation_features is not None)

        # sort feature columns
        binned = BinnedFeatures(features, self._max_bins)

        if checkpoint_path:
            tf.io.gfile.makedirs(checkpoint_path)
            logging.info("Checkpointing into path %s...", checkpoint_path)
            files = tf.io.gfile.listdir(checkpoint_path)
            if files:
                last_checkpoint = os.path.join(
                    checkpoint_path, sorted(files)[-1])
                logging.info(
                    "Restoring from previously saved checkpoint %s",
                    last_checkpoint)
                self.load_saved_model(last_checkpoint)

        # initial f(x)
        if len(self._trees) > 0:
            sum_prediction = self.batch_predict(features, get_raw_score=True)
        else:
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
            end_time = time.time()
            logging.info("Elapsed time for one round %s s",
                         str(end_time-begin_time))

            # save check point
            if checkpoint_path is not None:
                filename = os.path.join(
                    checkpoint_path,
                    'checkpoint-%04d.proto'%num_iter)
                logging.info(
                    "Saving checkpoint of iteration %d to %s",
                    num_iter, filename)
                self.save_model(filename)

            # save output
            if self._role != 'follower' and output_path is not None:
                pred = self._loss.predict(sum_prediction)
                metrics = self._loss.metrics(pred, labels)
                self._write_training_log(
                    output_path, 'train_%d'%num_iter, metrics, pred)

            # validation
            if validation_features is not None:
                val_pred = self.batch_predict(
                    validation_features, example_ids=validation_example_ids)
                if self._role != 'follower':
                    metrics = self._loss.metrics(val_pred, validation_labels)
                    logging.info(
                        "Validation metrics for iter %d: %s", num_iter, metrics)
                    if output_path is not None:
                        self._write_training_log(
                            output_path, 'val_%d'%num_iter, metrics, val_pred)


    def _fit_one_round_local(self, sum_fx, binned, labels):
        # compute grad and hess
        pred = self._loss.predict(sum_fx)
        grad = self._loss.gradient(sum_fx, pred, labels)
        hess = self._loss.hessian(sum_fx, pred, labels)
        logging.info(
            'Leader starting iteration %d. Metrics are %s',
            len(self._trees), self._loss.metrics(pred, labels))

        grower = BaseGrower(
            binned, grad, hess,
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
        self._bridge.start(self._bridge.new_iter_id())
        pred = self._loss.predict(sum_fx)
        grad = self._loss.gradient(sum_fx, pred, labels)
        hess = self._loss.hessian(sum_fx, pred, labels)
        print('Metrics: %s'%self._loss.metrics(pred, labels))
        _encrypt_and_send_numbers(
            self._bridge, 'grad', self._public_key, grad)
        _encrypt_and_send_numbers(
            self._bridge, 'hess', self._public_key, hess)
        self._bridge.commit()

        grower = LeaderGrower(
            self._bridge, self._public_key, self._private_key,
            binned, grad, hess,
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
        # compute grad and hess
        self._bridge.start(self._bridge.new_iter_id())
        grad = np.asarray(_receive_encrypted_numbers(
            self._bridge, 'grad', self._public_key))
        assert len(grad) == binned.features.shape[0]
        hess = np.asarray(_receive_encrypted_numbers(
            self._bridge, 'hess', self._public_key))
        assert len(hess) == binned.features.shape[0]
        self._bridge.commit()
        logging.info(
            'Follower starting iteration %d.',
            len(self._trees))

        grower = FollowerGrower(
            self._bridge, self._public_key,
            binned, grad, hess,
            learning_rate=self._learning_rate,
            max_depth=self._max_depth,
            max_leaves=self._max_leaves,
            l2_regularization=self._l2_regularization,
            grow_policy=self._grow_policy,
            num_parallel=self._num_parallel,
            pool=self._pool)
        grower.grow()

        return grower.to_proto()

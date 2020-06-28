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

import threading
import unittest
import numpy as np

import fedlearner as fl
from fedlearner.model.tree.tree import BoostingTreeEnsamble
from fedlearner.common import tree_model_pb2 as tree_pb2
from sklearn.datasets import load_iris


class TestBoostingTree(unittest.TestCase):
    def make_data(self):
        data = load_iris()
        X = data.data
        np.random.seed(123)
        mask = np.random.choice(a=[False, True], size=X.shape, p=[0.5, 0.5])
        X[mask] = float('nan')
        y = np.minimum(data.target, 1)
        return X, y

    def quantize_data(self, X):
        cat_X = np.zeros_like(X, dtype=np.int32)
        for i in range(X.shape[1]):
            x = X[:, i].copy()
            nan_mask = np.isnan(x)
            bins = np.quantile(x[~nan_mask], np.arange(33)/32)
            bins = np.unique(bins)
            cat_X[:, i][~nan_mask] = np.digitize(
                x[~nan_mask], bins, right=True)
            cat_X[:, i][nan_mask] = 33
        return cat_X

    def local_test_boosting_tree_helper(self, X, y, cat_X):
        booster = BoostingTreeEnsamble(
            None,
            max_iters=3,
            max_depth=2,
            num_parallel=2)
        train_pred = booster.fit(X, y, cat_features=cat_X)
        pred = booster.batch_predict(X, cat_features=cat_X)
        np.testing.assert_almost_equal(train_pred, pred)
        return pred

    def leader_test_boosting_tree_helper(self, X, y, cat_X):
        bridge = fl.trainer.bridge.Bridge(
            'leader', 50051, 'localhost:50052', streaming_mode=False)
        booster = BoostingTreeEnsamble(
            bridge,
            max_iters=3,
            max_depth=2)
        train_pred = booster.fit(X, y, cat_features=cat_X)
        pred = booster.batch_predict(X, cat_features=cat_X)
        bridge.terminate()
        np.testing.assert_almost_equal(train_pred, pred)
        return pred

    def follower_test_boosting_tree_helper(self, X, cat_X):
        bridge = fl.trainer.bridge.Bridge(
            'follower', 50052, 'localhost:50051', streaming_mode=False)
        booster = BoostingTreeEnsamble(
            bridge,
            max_iters=3,
            max_depth=2)
        booster.fit(X, None, cat_features=cat_X)
        pred = booster.batch_predict(X, cat_features=cat_X, get_raw_score=True)
        bridge.terminate()
        np.testing.assert_almost_equal(pred, 0)

    def boosting_tree_helper(self, X, y, cat_X):
        local_pred = self.local_test_boosting_tree_helper(X, y, cat_X)
        self.assertGreater(sum((local_pred > 0.5) == y)/len(y), 0.90)

        leader_X = X[:, :X.shape[1]//2]
        follower_X = X[:, X.shape[1]//2:]
        if cat_X is not None:
            leader_cat_X = cat_X[:, :cat_X.shape[1]//2]
            follower_cat_X = cat_X[:, cat_X.shape[1]//2:]
        else:
            leader_cat_X = follower_cat_X = None

        # test two side
        thread = threading.Thread(
            target=self.follower_test_boosting_tree_helper,
            args=(follower_X, follower_cat_X))
        thread.start()
        leader_pred = self.leader_test_boosting_tree_helper(
            leader_X, y, leader_cat_X)
        thread.join()
        np.testing.assert_almost_equal(local_pred, leader_pred)

        # test one side
        thread = threading.Thread(
            target=self.follower_test_boosting_tree_helper,
            args=(X, cat_X))
        thread.start()
        leader_pred = self.leader_test_boosting_tree_helper(
            np.zeros((X.shape[0], 0)), y, None)
        thread.join()
        np.testing.assert_almost_equal(local_pred, leader_pred)

    def test_boosting_tree(self):
        X, y = self.make_data()

        self.boosting_tree_helper(X, y, None)

        cat_X = self.quantize_data(X[:, 2:])
        cont_X = X[:, :2]

        self.boosting_tree_helper(cont_X, y, cat_X)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    unittest.main()

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
from fedlearner.model.crypto import paillier
from sklearn.datasets import load_iris

paillier.NOISE_GENS = 1024


class TestBoostingTree(unittest.TestCase):
    def make_data(self):
        data = load_iris()
        X = data.data
        np.random.seed(123)
        mask = np.random.choice(a=[False, True], size=X.shape, p=[0.5, 0.5])
        X[mask] = float('nan')
        y = np.minimum(data.target, 1)
        return X, y

    def local_test_boosting_tree_helper(self, X, y):
        booster = BoostingTreeEnsamble(
            None,
            max_iters=5,
            max_depth=3,
            num_parallel=2)
        booster.fit(X, y)
        pred = booster.batch_predict(X)
        return pred

    def leader_test_boosting_tree_helper(self, X, y):
        bridge = fl.trainer.bridge.Bridge(
            'leader', 50051, 'localhost:50052', streaming_mode=False)
        booster = BoostingTreeEnsamble(
            bridge,
            max_iters=5,
            max_depth=3)
        booster.fit(X, y)
        pred = booster.batch_predict(X)
        bridge.terminate()
        return pred

    def follower_test_boosting_tree_helper(self, X):
        bridge = fl.trainer.bridge.Bridge(
            'follower', 50052, 'localhost:50051', streaming_mode=False)
        booster = BoostingTreeEnsamble(
            bridge,
            max_iters=5,
            max_depth=3)
        booster.fit(X, None)
        pred = booster.batch_predict(X)
        bridge.terminate()

    def test_boosting_tree(self):
        X, y = self.make_data()
        local_pred = self.local_test_boosting_tree_helper(X, y)
        self.assertGreater(sum((local_pred > 0.5) == y)/len(y), 0.90)

        leader_X = X[:, :X.shape[1]//2]
        follower_X = X[:, X.shape[1]//2:]

        # test two side
        thread = threading.Thread(
            target=self.follower_test_boosting_tree_helper,
            args=(follower_X,))
        thread.start()
        leader_pred = self.leader_test_boosting_tree_helper(leader_X, y)
        thread.join()
        self.assertTrue(np.allclose(local_pred, leader_pred))

        # test one side
        thread = threading.Thread(
            target=self.follower_test_boosting_tree_helper,
            args=(X,))
        thread.start()
        leader_pred = self.leader_test_boosting_tree_helper(
            np.zeros((X.shape[0], 0)), y)
        thread.join()
        self.assertTrue(np.allclose(local_pred, leader_pred))


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()

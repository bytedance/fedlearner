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

import unittest
import numpy as np

from fedlearner.model.tree.tree import BoostingTreeEnsamble
from fedlearner.common import tree_model_pb2 as tree_pb2
from sklearn.datasets import load_iris


class TestBoostingTree(unittest.TestCase):
    def test_boosting_tree_local(self):
        data = load_iris()
        X = data.data
        mask = np.random.choice(a=[False, True], size=X.shape, p=[0.5, 0.5])
        X[mask] = float('nan')
        y = np.minimum(data.target, 1)
        booster = BoostingTreeEnsamble(
            None,
            max_iters=5,
            max_depth=3,
            num_parallel=2)
        booster.fit(X, y)
        pred = booster.batch_predict(X)
        self.assertGreater(sum((pred > 0.5) == y)/len(y), 0.94)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    unittest.main()

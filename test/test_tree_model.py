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
    def test_boosting_tree(self):
        proto = tree_pb2.BoostingTreeEnsambleProto(
            params=tree_pb2.BoostingParamsProto(
                num_rounds=2,
                max_depth=3,
                lam=1.0,
                sketch_eps=0.2))
        booster = BoostingTreeEnsamble(proto)

        data = load_iris()
        labels = data.target
        labels = np.minimum(labels, 1)
        features = {str(i): data.data[:, i] for i in range(data.data.shape[1])}
        booster.fit(None, [i for i in range(len(data.target))], features, labels)


if __name__ == '__main__':
    unittest.main()

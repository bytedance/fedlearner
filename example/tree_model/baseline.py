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
# pylint: disable=unused-import

import numpy as np
from sklearn.experimental import enable_hist_gradient_boosting
from sklearn.ensemble import HistGradientBoostingClassifier

def train():
    with open('data/local_train.csv', 'rb') as fin:
        data = np.loadtxt(fin, delimiter=',')
        X = data[:, :-1]
        y = data[:, -1]
    with open('data/local_test.csv', 'rb') as fin:
        data = np.loadtxt(fin, delimiter=',')
        Xt = data[:, :-1]
        yt = data[:, -1]
    booster = HistGradientBoostingClassifier(
        verbose=1, max_bins=33, learning_rate=0.3, max_iter=5, max_depth=3,
        l2_regularization=1.0, max_leaf_nodes=None)
    booster.fit(X, y)
    print('train', booster.score(X, y))
    print('test', booster.score(Xt, yt))

if __name__ == '__main__':
    train()

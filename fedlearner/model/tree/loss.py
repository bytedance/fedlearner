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

import numpy as np
from scipy import special as sp_special


class LogisticLoss(object):
    def __init__(self):
        pass

    def predict(self, x):
        return sp_special.expit(x)

    def loss(self, x, pred, label):
        return np.zeros_like(pred)

    def gradient(self, x, pred, label):
        return pred - label

    def hessian(self, x, pred, label):
        return np.maximum(pred * (1.0 - pred), 1e-16)

    def metrics(self, pred, label):
        return {
            'acc': sum((pred > 0.5) == label) / len(label)
        }

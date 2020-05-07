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
from sklearn.metrics import f1_score, roc_auc_score, \
                            precision_score, recall_score


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
        y_pred = (pred > 0.5).astype(label.dtype)
        return {
            'acc': sum(y_pred == label) / len(label),
            'precision': precision_score(label, y_pred),
            'recall': recall_score(label, y_pred),
            'f1': f1_score(label, y_pred),
            'auc': roc_auc_score(label, pred)
        }

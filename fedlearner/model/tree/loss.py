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


def _roc_auc_score(label, pred):
    p = np.argsort(pred, kind='mergesort')[::-1]
    label = label[p]
    pred = pred[p]
    unique = np.r_[np.where(np.diff(pred))[0], label.size-1]
    tps = np.cumsum(label)[unique]
    fps = np.cumsum(1 - label)[unique]
    tpr = np.r_[0, tps] / tps[-1]
    fpr = np.r_[0, fps] / fps[-1]
    ks = (tpr-fpr).max()
    auc = np.trapz(tpr, x=fpr)
    return ks, auc

def _precision_recall_f1(label, y_pred):
    tp = (label  * y_pred).sum()
    precision = tp / (y_pred.sum() + 1e-16)
    recall = tp / (label.sum() + 1e-16)
    f1 = 2 * precision * recall / (precision + recall + 1e-16)

    return precision, recall, f1

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

    @staticmethod
    def confusion_matrix(pred, label):
        tp = (label * pred).sum()
        tn = ((1 - label) * (1 - pred)).sum()
        fp = ((1 - label) * pred).sum()
        fn = (label * (1 - pred)).sum()
        return {'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn}

    def metrics(self, pred, label):
        y_pred = (pred > 0.5).astype(label.dtype)
        precision, recall, f1 = _precision_recall_f1(label, y_pred)
        ks, auc = _roc_auc_score(label, pred)
        metrics = {
            'acc': np.isclose(y_pred, label).sum() / len(label),
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'auc': auc,
            'ks': ks,
        }
        conf_mat = self.confusion_matrix(y_pred, label)
        metrics.update(conf_mat)
        return metrics


class MSELoss(object):
    def __init__(self):
        pass

    def predict(self, x):
        return x

    def loss(self, x, pred, label):
        return np.square(pred - label).mean() / 2.0

    def gradient(self, x, pred, label):
        return pred - label

    def hessian(self, x, pred, label):
        return np.ones_like(pred)

    def metrics(self, pred, label):
        mse = np.square(pred - label).mean()
        msre = np.sqrt(mse)
        fabs = np.abs(pred - label).mean()
        return {
            'mse': mse,
            'msre': msre,
            'abs': fabs,
        }

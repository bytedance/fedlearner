import tensorflow as tf
import numpy as np


def _init_data():
    data = tf.keras.datasets.mnist.load_data()
    return data[0][0], data[0][1], data[1][0], data[1][1]


class MnistData:
    def __init__(self):
        self.data = tf.keras.datasets.mnist.load_data()
        self.train_sample, self.train_label, self.test_sample, self.test_label = _init_data()
        self.train_idx = 0
        self.test_idx = 0
        self._num_sample = len(self.train_sample)

    def __len__(self):
        return self._num_sample

    def train_batch(self):
        batch_size = 32
        if self.train_idx % len(self) == 0:
            self.train_idx = 0
            rand_perm = np.arange(len(self))
            np.random.shuffle(rand_perm)
            self.train_sample = self.train_sample[rand_perm]
            self.train_label = self.train_label[rand_perm]
        return_sample = self.train_sample[self.train_idx:self.train_idx + batch_size]
        return_label = self.train_label[self.train_idx:self.train_idx + batch_size]
        return return_sample, return_label

    def test_batch(self):
        batch_size = 16
        if self.test_idx % len(self.test_sample) == 0:
            self.test_idx = 0
        begin = self.test_idx
        end = self.test_idx + batch_size
        self.test_idx = end
        return self.test_sample[begin:end], self.test_label[begin:end]

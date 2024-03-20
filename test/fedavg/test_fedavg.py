import threading
import unittest
import tensorflow as tf
import numpy as np
import fedlearner.common.fl_logging as logging
from fedlearner.fedavg import train_from_keras_model

(x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
x_train = x_train.reshape(x_train.shape[0], -1).astype(np.float32) / 255.0
y_train = y_train.astype(np.int32)

x_test = x_test.reshape(x_test.shape[0], -1).astype(np.float32) / 255.0
y_test = y_test.astype(np.int32)


def create_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(200, activation='relu', input_shape=(784, )),
        tf.keras.layers.Dense(200, activation='relu'),
        tf.keras.layers.Dense(10, activation='softmax'),
    ])
    model.compile(optimizer=tf.keras.optimizers.SGD(0.01),
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                  metrics=['acc'])
    return model

class TestFedavgTrain(unittest.TestCase):
    def setUp(self):
        super(TestFedavgTrain, self).__init__()
        self._fl_cluster = {
            "leader": {
              "name": "leader",
              "address": "0.0.0.0:20050"
            },
            "followers": [{
              "name": "follower"
            }]
        }
        self._batch_size = 64
        self._epochs = 1
        self._steps_per_sync = 10
        self._l_eval_result = None
        self._f_eval_result = None

    def _train_leader(self):
        x = x_train[:len(x_train) // 2]
        y = y_train[:len(y_train) // 2]
        model = create_model()
        train_from_keras_model(model,
                               x,
                               y,
                               batch_size=self._batch_size,
                               epochs=self._epochs,
                               fl_name="leader",
                               fl_cluster=self._fl_cluster,
                               steps_per_sync=self._steps_per_sync)
        self._l_eval_result = model.evaluate(x_test, y_test)

    def _train_follower(self):
        x = x_train[len(x_train) // 2:]
        y = y_train[len(y_train) // 2:]
        model = create_model()
        train_from_keras_model(model,
                               x,
                               y,
                               batch_size=self._batch_size,
                               epochs=self._epochs,
                               fl_name="follower",
                               fl_cluster=self._fl_cluster,
                               steps_per_sync=self._steps_per_sync)
        self._f_eval_result = model.evaluate(x_test, y_test)


    def test_train(self):
        l_thread = threading.Thread(target=self._train_leader)
        f_thread = threading.Thread(target=self._train_follower)
        l_thread.start()
        f_thread.start()
        l_thread.join()
        f_thread.join()

        assert len(self._l_eval_result) == 2
        assert len(self._f_eval_result) == 2
        for v1, v2 in zip(self._l_eval_result, self._f_eval_result):
            assert np.isclose(v1, v2)


if __name__ == '__main__':
    logging.set_level("debug")
    unittest.main()

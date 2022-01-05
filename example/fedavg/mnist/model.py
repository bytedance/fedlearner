import tensorflow as tf
import numpy as np

(x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
x_train = x_train.reshape(x_train.shape[0], -1).astype(np.float32) / 255.0
y_train = y_train.astype(np.int32)

x_test = x_test.reshape(x_test.shape[0], -1).astype(np.float32) / 255.0
y_test = y_test.astype(np.int32)

def create_model():
  model = tf.keras.Sequential([
    tf.keras.layers.Dense(200, activation='relu', input_shape=(784,)),
    tf.keras.layers.Dense(200, activation='relu'),
    tf.keras.layers.Dense(10, activation='softmax'),
  ])
  model.compile(optimizer=tf.keras.optimizers.SGD(0.01),
                loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                metrics='acc')
  return model
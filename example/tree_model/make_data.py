import os
import numpy as np
import tensorflow as tf


def process_data(X, y, role):
    X = X.reshape(X.shape[0], -1)
    X = np.asarray([X[i] for i, yi in enumerate(y) if yi in (2, 3)])
    y = np.asarray([[y[i] == 3] for i, yi in enumerate(y) if yi in (2, 3)],
                   dtype=np.int32)
    if role == 'leader':
        data = np.concatenate((X[:, :X.shape[1]//2], y), axis=1)
    elif role == 'follower':
        data = X[:, X.shape[1]//2:]
    else:
        data = np.concatenate((X, y), axis=1)
    return data

def make_data():
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
    if not os.path.exists('data'):
        os.makedirs('data')
    np.savetxt(
        'data/leader_train.csv',
        process_data(x_train, y_train, 'leader'),
        delimiter=',')
    np.savetxt(
        'data/follower_train.csv',
        process_data(x_train, y_train, 'follower'),
        delimiter=',')
    np.savetxt(
        'data/local_train.csv',
        process_data(x_train, y_train, 'local'),
        delimiter=',')

    np.savetxt(
        'data/leader_test.csv',
        process_data(x_test, y_test, 'leader'),
        delimiter=',')
    np.savetxt(
        'data/follower_test.csv',
        process_data(x_test, y_test, 'follower'),
        delimiter=',')
    np.savetxt(
        'data/local_test.csv',
        process_data(x_test, y_test, 'local'),
        delimiter=',')


if __name__ == '__main__':
    make_data()

import os
import argparse

import numpy as np
import tensorflow as tf
from sklearn.datasets import load_iris


def process_data(X, y, role, verify_example_ids):
    if role == 'leader':
        data = np.concatenate((X[:, :X.shape[1]//2], y), axis=1)
    elif role == 'follower':
        data = X[:, X.shape[1]//2:]
    else:
        data = np.concatenate((X, y), axis=1)

    if verify_example_ids:
        data = np.concatenate(
            [[[i] for i in range(data.shape[0])], data], axis=1)
    return data

def process_mnist(X, y):
    X = X.reshape(X.shape[0], -1)
    X = np.asarray([X[i] for i, yi in enumerate(y) if yi in (2, 3)])
    y = np.asarray([[y[i] == 3] for i, yi in enumerate(y) if yi in (2, 3)],
                dtype=np.int32)
    return X, y

def make_data(args):
    if args.dataset == 'mnist':
        (x_train, y_train), (x_test, y_test) = \
            tf.keras.datasets.mnist.load_data()
        x_train, y_train = process_mnist(x_train, y_train)
        x_test, y_test = process_mnist(x_test, y_test)
    else:
        data = load_iris()
        x_train = x_test = data.data
        y_train = y_test = np.minimum(data.target, 1).reshape(-1, 1)

    if not os.path.exists('data'):
        os.makedirs('data')
        os.makedirs('data/leader_test')
        os.makedirs('data/follower_test')
        os.makedirs('data/local_test')

    np.savetxt(
        'data/leader_train.data',
        process_data(x_train, y_train, 'leader', args.verify_example_ids),
        delimiter=',')
    np.savetxt(
        'data/follower_train.data',
        process_data(x_train, y_train, 'follower', args.verify_example_ids),
        delimiter=',')
    np.savetxt(
        'data/local_train.data',
        process_data(x_train, y_train, 'local', False),
        delimiter=',')

    np.savetxt(
        'data/leader_test/part-0001.data',
        process_data(x_test, y_test, 'leader', args.verify_example_ids),
        delimiter=',')
    np.savetxt(
        'data/follower_test/part-0001.data',
        process_data(x_test, y_test, 'follower', args.verify_example_ids),
        delimiter=',')
    np.savetxt(
        'data/local_test/part-0001.data',
        process_data(x_test, y_test, 'local', False),
        delimiter=',')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='FedLearner Tree Model Trainer.')
    parser.add_argument('--verify-example-ids',
                        type=bool,
                        default=False,
                        help='If set to true, the first column of the '
                             'data will be treated as example ids that '
                             'must match between leader and follower')
    parser.add_argument('--dataset', type=str, default='mnist',
                        help='whether to use mnist or iris dataset')
    make_data(parser.parse_args())

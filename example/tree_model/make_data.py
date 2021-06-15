# pylint: disable=unsubscriptable-object
import os
import argparse

import numpy as np
import tensorflow.compat.v1 as tf
from sklearn.datasets import load_iris


def quantize_data(header, dtypes, X):
    for i, (h, dtype) in enumerate(zip(header, dtypes)):
        if h[0] != 'f' or dtype != np.int32:
            continue
        x = X[:, i].copy()
        nan_mask = np.isnan(x)
        bins = np.quantile(x[~nan_mask], np.arange(33)/32)
        bins = np.unique(bins)
        X[:, i][~nan_mask] = np.digitize(
            x[~nan_mask], bins, right=True)
        X[:, i][nan_mask] = 33

    return np.asarray([tuple(i) for i in X], dtype=list(zip(header, dtypes)))

def write_tfrecord_data(filename, data, header, dtypes):
    fout = tf.io.TFRecordWriter(filename)
    for i in range(data.shape[0]):
        example = tf.train.Example()
        for h, d, x in zip(header, dtypes, data[i]):
            if d == np.int32:
                example.features.feature[h].int64_list.value.append(x)
            else:
                example.features.feature[h].float_list.value.append(x)
        fout.write(example.SerializeToString())

def write_data(output_type, filename, X, y, role, verify_example_ids):
    if role == 'leader':
        data = np.concatenate((X[:, :X.shape[1]//2], y), axis=1)
        N = data.shape[1]-1
        header = ['f%05d'%i for i in range(N)] + ['label']
        dtypes = [np.float]*(N//2) + [np.int32]*(N - N//2) + [np.int32]
    elif role == 'follower':
        data = X[:, X.shape[1]//2:]
        N = data.shape[1]
        header = ['f%05d'%i for i in range(N)]
        dtypes = [np.float]*(N//2) + [np.int32]*(N - N//2)
    else:
        data = np.concatenate((X, y), axis=1)
        N = data.shape[1]-1
        header = ['f%05d'%i for i in range(N)] + ['label']
        dtypes = [np.float]*(N//2) + [np.int32]*(N - N//2) + [np.int32]

    if verify_example_ids:
        data = np.concatenate(
            [[[i] for i in range(data.shape[0])], data], axis=1)
        header = ['example_id'] + header
        dtypes = [np.int32] + dtypes

    data = quantize_data(header, dtypes, data)
    if output_type == 'tfrecord':
        write_tfrecord_data(filename, data, header, dtypes)
    else:
        np.savetxt(
            filename,
            data,
            delimiter=',',
            header=','.join(header),
            fmt=['%d' if i == np.int32 else '%f' for i in dtypes],
            comments='')

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

    write_data(
        args.output_type,
        'data/leader_train.%s'%args.output_type, x_train, y_train,
        'leader', args.verify_example_ids)
    write_data(
        args.output_type,
        'data/follower_train.%s'%args.output_type, x_train, y_train,
        'follower', args.verify_example_ids)
    write_data(
        args.output_type,
        'data/local_train.%s'%args.output_type, x_train, y_train,
        'local', False)

    write_data(
        args.output_type,
        'data/leader_test/part-0001.%s'%args.output_type, x_test, y_test,
        'leader', args.verify_example_ids)
    write_data(
        args.output_type,
        'data/follower_test/part-0001.%s'%args.output_type, x_test, y_test,
        'follower', args.verify_example_ids)
    write_data(
        args.output_type,
        'data/local_test/part-0001.%s'%args.output_type, x_test, y_test,
        'local', False)

    write_data(
        args.output_type,
        'data/leader_test/part-0002.%s'%args.output_type, x_test, y_test,
        'leader', args.verify_example_ids)
    write_data(
        args.output_type,
        'data/follower_test/part-0002.%s'%args.output_type, x_test, y_test,
        'follower', args.verify_example_ids)
    write_data(
        args.output_type,
        'data/local_test/part-0002.%s'%args.output_type, x_test, y_test,
        'local', False)


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
    parser.add_argument('--output-type', type=str, default='csv',
                        help='Output csv or tfrecord')
    make_data(parser.parse_args())

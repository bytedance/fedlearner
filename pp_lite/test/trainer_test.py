# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import numpy as np
import time
import unittest
import json

import tensorflow.compat.v1 as tf
import shutil
from multiprocessing import get_context

from pp_lite.trainer.client.client import main as client_main
from pp_lite.trainer.server.server import main as server_main
from pp_lite.proto.arguments_pb2 import TrainerArguments


class IntegratedTest(unittest.TestCase):

    def test_e2e(self):
        logging.basicConfig(level=logging.INFO)
        cluster_spec_str = json.dumps({
            'master': ['localhost:50101'],
            'ps': ['localhost:50102', 'localhost:50104'],
            'worker': ['localhost:50103', 'localhost:50105']
        })
        cluster_spec_dict = json.loads(cluster_spec_str)
        if isinstance(cluster_spec_dict, dict):
            for name, addrs in cluster_spec_dict.items():
                if name in ['master', 'ps', 'worker'] and isinstance(addrs, list):
                    for addr in addrs:
                        if not isinstance(addr, str):
                            raise TypeError('Input cluster_spec type error')
                else:
                    raise TypeError('Input cluster_spec type error')
        else:
            raise TypeError('Input cluster_spec type error')

        args = TrainerArguments(data_path='pp_lite/trainer/data/',
                                file_wildcard='**/*',
                                export_path='pp_lite/trainer/model/',
                                server_port=55550,
                                tf_port=51001,
                                num_clients=1,
                                cluster_spec=cluster_spec_str,
                                model_version=0,
                                model_max_to_keep=5,
                                tolerated_version_gap=1,
                                task_mode='local',
                                local_steps=100,
                                batch_size=10,
                                master_addr='localhost:55555',
                                ps_rank=0,
                                worker_rank=0,
                                save_version_gap=10)

        # generate TFRecord
        if not tf.io.gfile.exists(args.data_path):
            logging.info('Generating data ...')
            tf.io.gfile.makedirs(args.data_path)

            (x, y), _ = tf.keras.datasets.mnist.load_data()
            x = x.reshape((x.shape[0], -1)) / 255
            n = 1000
            num = x.shape[0] // n
            for idx in range(num):
                np_to_tfrecords(x[idx * n:idx * n + n], y[idx * n:idx * n + n], f'{args.data_path}{idx}')

        context = get_context('spawn')

        process_server = context.Process(target=server_main, args=(args,), daemon=True)
        process_server.start()
        time.sleep(1)

        cluster_spec_dict['master'] = ['localhost:50201']
        args.cluster_spec = json.dumps(cluster_spec_dict)
        client_main(args=args)
        process_server.join()

        shutil.rmtree(args.data_path, ignore_errors=False, onerror=None)
        shutil.rmtree(args.export_path, ignore_errors=False, onerror=None)


def _bytes_feature(value):
    if isinstance(value, type(tf.constant(0))):  # if value ist tensor
        value = value.numpy()  # get value of tensor
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def _float_feature(value):
    return tf.train.Feature(float_list=tf.train.FloatList(value=value))


def _int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


def serialize_array(array):
    array = tf.io.serialize_tensor(array)
    return array


def np_to_tfrecords(X, Y, file_path_prefix):
    # Generate tfrecord writer
    result_tf_file = file_path_prefix + '.tfrecords'
    writer = tf.python_io.TFRecordWriter(result_tf_file)

    # iterate over each sample,
    # and serialize it as ProtoBuf.
    # temporarily enable eager execution so _bytes_feature can call Tensor.numpy()
    tf.enable_eager_execution()
    for idx in range(X.shape[0]):
        x = X[idx]
        y = Y[idx]
        data = {
            'X': _bytes_feature(tf.serialize_tensor(x.astype(np.float32))),
            'X_size': _int64_feature(x.shape[0]),
            'Y': _int64_feature(y)
        }
        features = tf.train.Features(feature=data)
        example = tf.train.Example(features=features)
        serialized = example.SerializeToString()
        writer.write(serialized)
    tf.disable_eager_execution()


if __name__ == '__main__':
    unittest.main()

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

import os
import time
import tensorflow as tf
import numpy as np
import logging
from datetime import datetime
from fedlearner.fedavg import train_from_keras_model
from metrics import MetricsKerasCallback

LOAD_MODEL_FROM = os.getenv('LOAD_MODEL_FROM')  # load from {STORAGE_ROOT}/job_outputs/{job.name}/checkpoints
OUTPUT_BASE_DIR = os.getenv('OUTPUT_BASE_DIR')  # save output under {OUTPUT_BASE_DIR}/output
EXPORT_PATH = os.path.join(OUTPUT_BASE_DIR, 'exported_models')  # save estimator to {EXPORT_PATH}
CHECKPOINT_PATH = os.path.join(OUTPUT_BASE_DIR, 'checkpoints')  # save keras model to {CHECKPOINT_PATH}

fl_leader_address = os.getenv('FL_LEADER_ADDRESS', '0.0.0.0:6870')
FL_CLUSTER = {'leader': {'name': 'leader', 'address': fl_leader_address}, 'followers': [{'name': 'follower'}]}


def _label_to_int(label: str):
    pred_fn_pairs = [(tf.equal(label, 'deer'), lambda: 0), (tf.equal(label, 'frog'), lambda: 1),
                     (tf.equal(label, 'horse'), lambda: 2), (tf.equal(label, 'dog'), lambda: 3),
                     (tf.equal(label, 'automobile'), lambda: 4), (tf.equal(label, 'airplane'), lambda: 5),
                     (tf.equal(label, 'ship'), lambda: 6), (tf.equal(label, 'cat'), lambda: 7),
                     (tf.equal(label, 'truck'), lambda: 8), (tf.equal(label, 'bird'), lambda: 9)]
    return tf.case(pred_fn_pairs)


def decode_and_resize(args):
    x, h, w, c = args
    x = tf.io.decode_raw(x, tf.uint8)
    x = tf.reshape(x, [h, w, c])
    x = tf.image.resize(x, (128, 128))
    x = tf.cast(x, tf.float32)
    x = tf.image.per_image_standardization(x)
    x.set_shape([128, 128, 3])
    return x


def serving_input_receiver_fn():
    feature_map = {
        'width': tf.io.FixedLenFeature([], tf.int64),
        'height': tf.io.FixedLenFeature([], tf.int64),
        'nChannels': tf.io.FixedLenFeature([], tf.int64),
        'data': tf.io.FixedLenFeature([], tf.string)
    }
    record_batch = tf.placeholder(dtype=tf.string, name='examples')
    features = tf.io.parse_example(record_batch, features=feature_map)
    features['data'] = tf.map_fn(decode_and_resize,
                                 (features['data'], features['height'], features['width'], features['nChannels']),
                                 dtype=tf.float32)
    receiver_tensors = {'examples': record_batch}
    return tf.estimator.export.ServingInputReceiver({'data': features['data']}, receiver_tensors)


def parse_fn(record: bytes):
    features = tf.io.parse_single_example(
        record, {
            'width': tf.io.FixedLenFeature([], tf.int64),
            'height': tf.io.FixedLenFeature([], tf.int64),
            'nChannels': tf.io.FixedLenFeature([], tf.int64),
            'label': tf.io.FixedLenFeature([], tf.string),
            'data': tf.io.FixedLenFeature([], tf.string)
        })
    label = _label_to_int(features['label'])
    img = tf.decode_raw(features['data'], out_type=tf.uint8)
    img = tf.reshape(img, [features['height'], features['width'], features['nChannels']])
    img = tf.image.resize(img, size=[128, 128])
    img = tf.cast(img, tf.float32)
    return img, label


def create_model():
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(128, 128, 3), name='data'),
        tf.keras.layers.Conv2D(16, kernel_size=(3, 3), activation='relu'),
        tf.keras.layers.Conv2D(32, kernel_size=(3, 3), activation='relu'),
        tf.keras.layers.Conv2D(64, kernel_size=(3, 3), activation='relu'),
        tf.keras.layers.GlobalMaxPool2D(),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(16, activation='relu'),
        tf.keras.layers.Dense(10, activation='softmax', name='label'),
    ])
    model.compile(optimizer=tf.keras.optimizers.Adam(0.001),
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                  metrics=['acc'])
    return model


def get_dataset(data_path: str):
    files = []
    for dirname, subdirs, filenames in tf.io.gfile.walk(data_path):
        for filename in filenames:
            if filename.startswith('part'):
                files.append(os.path.join(dirname, filename))
    print('list filenames: ', files)
    ds = tf.data.TFRecordDataset(files) \
        .map(map_func=parse_fn) \
        .shuffle(30000) \
        .batch(30) \
        .prefetch(10)
    return ds


def run(fl_name, mode, ds, epoch_num, steps_per_sync):
    if mode == 'train':
        model = create_model()
        model.build([None, 128, 128, 3])
        train_from_keras_model(model,
                               x=ds,
                               y=None,
                               epochs=epoch_num,
                               fl_name=fl_name,
                               fl_cluster=FL_CLUSTER,
                               steps_per_sync=steps_per_sync)
        estimator = tf.keras.estimator.model_to_estimator(model)
        # since fedlearner will save keras model, sleep for model importer to import the latest model
        time.sleep(60)
        export_path = estimator.export_saved_model(EXPORT_PATH, serving_input_receiver_fn=serving_input_receiver_fn)
        logging.info(f'\nexport estimator to {export_path}\n')
        checkpoint_path = os.path.join(CHECKPOINT_PATH, str(int(datetime.now().timestamp())))
        model.save(checkpoint_path, save_format='tf')
        logging.info(f'\nexport model to {CHECKPOINT_PATH}\n')
    else:
        latest_path = os.path.join(LOAD_MODEL_FROM, sorted(tf.io.gfile.listdir(LOAD_MODEL_FROM))[-1])
        logging.info('load model from %s', latest_path)
        model = tf.keras.models.load_model(latest_path)
        if mode == 'eval':
            model.evaluate(ds, callbacks=[MetricsKerasCallback()])
            output = model.predict(ds)
            output_path = os.path.join(OUTPUT_BASE_DIR, 'outputs')
            tf.io.gfile.makedirs(output_path)
            logging.info('write output to %s', output_path)
            with tf.io.gfile.GFile(os.path.join(output_path, 'output.csv'), 'w') as fp:
                np.savetxt(fp, output)

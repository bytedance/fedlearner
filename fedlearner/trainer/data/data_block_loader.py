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

try:
    import queue
except ImportError:
    import Queue as queue
import logging
import tensorflow.compat.v1 as tf

class DataBlockLoader(object):
    def __init__(self, batch_size, role, bridge, trainer_master):
        self._batch_size = batch_size
        self._role = role
        self._bridge = bridge
        self._trainer_master = trainer_master
        assert self._trainer_master is not None

        self._count = 0
        if role == 'follower':
            self._block_queue = queue.Queue()
            self._bridge.register_data_block_handler(self._data_block_handler)

    def _data_block_handler(self, msg):
        logging.info('DataBlock: recv "%s" at %d', msg.block_id, msg.count)
        assert self._count == msg.count
        if not msg.block_id:
            block = None
        else:
            block = self._trainer_master.request_data_block(msg.block_id)
            if block is None:
                return False
        self._count += 1
        self._block_queue.put(block)
        return True

    def get_next_block(self):
        if self._role == 'leader':
            while True:
                block = self._trainer_master.request_data_block()
                if block is not None:
                    if not self._bridge.load_data_block(
                            self._count, block.block_id):
                        continue
                else:
                    self._bridge.load_data_block(self._count, '')
                break
            self._count += 1
        else:
            block = self._block_queue.get()
        return block

    def make_dataset(self):
        def gen():
            while True:
                block = self.get_next_block()
                if not block:
                    break
                yield block.data_path

        dataset = tf.data.Dataset.from_generator(gen, tf.string)
        dataset = tf.data.TFRecordDataset(dataset)
        dataset = dataset.batch(self._batch_size, drop_remainder=True)
        dataset = dataset.prefetch(2)
        return dataset

    def make_batch_iterator(self):
        return self.make_dataset().make_one_shot_iterator()

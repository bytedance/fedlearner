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

import argparse
import logging
import os
import random

from fedlearner.trainer_master.data.data_block_queue import DataBlockQueue
from fedlearner.data_join.data_block_visitor import DataBlockVisitor
from fedlearner.data_join.common import get_kvstore_config
from .trainer_master import TrainerMaster

kvstore_type = os.environ.get('KVSTORE_TYPE', 'etcd')
db_database, db_addr, db_username, db_password, db_base_dir = \
    get_kvstore_config(kvstore_type)

class LeaderTrainerMaster(TrainerMaster):
    def __init__(self, application_id, data_source,
                 start_time, end_time, online_training,
                 shuffle_data_block, epoch_num):
        super(LeaderTrainerMaster, self).__init__(application_id,
                                                  None, online_training)
        kvstore_use_mock = os.environ.get('KVSTORE_USE_MOCK', "off") == "on"
        self._data_block_queue = DataBlockQueue()
        self._data_block_visitor = DataBlockVisitor(
            data_source, db_database, db_base_dir, db_addr,
                db_username, db_password, kvstore_use_mock)
        self._start_time = start_time
        self._end_time = end_time
        self._epoch_num = epoch_num
        self._shuffle_data_block = shuffle_data_block
        if online_training:
            self._epoch_num = 1
            self._shuffle_data_block = False
            logging.warning("Online Training will ignore args "\
                            "epoch and shuffle data block")
        assert self._epoch_num >= 1, \
                "epoch_num {} must >= 1".format(self._epoch_num)

    def _load_data(self):
        checkpoint = self._get_checkpoint()
        # pylint: disable=line-too-long
        visitor = self._data_block_visitor
        data_block_reps = [dbr for dbr in visitor.LoadDataBlockRepByTimeFrame(
                           self._start_time, self._end_time).values()
                           if dbr.block_id not in checkpoint]
        if self._online_training:
            data_block_reps.sort(key=dbr.data_block_index)
        for rnd in range(self._epoch_num):
            if self._shuffle_data_block:
                random.shuffle(data_block_reps)
            for dbr in data_block_reps:
                logging.debug('epoch round-%d: add data block id %s path %s',
                               rnd, dbr.block_id, dbr.data_block_fpath)
                self._data_block_queue.put(dbr)

    def _alloc_data_block(self, block_id=None):
        # block_id is unused in leader role
        data_blocks_resp = None
        if not self._data_block_queue.empty():
            data_blocks_resp = self._data_block_queue.get()
            with self._checkpoint_mutex:
                self._allocated_data_blockids.add(data_blocks_resp.block_id)
        return data_blocks_resp


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser('leader trainer master cmd.')
    parser.add_argument('-p', '--port', type=int, default=50001,
                        help='Listen port of leader trainer master')
    parser.add_argument('-app_id', '--application_id',
                        required=True, help='application_id')
    parser.add_argument('-data_source', '--data_source',
                        required=False, help='training example data source')
    parser.add_argument('-start_date', '--start_date',
                        default=None, help='training data start date')
    parser.add_argument('-end_date', '--end_date',
                        default=None, help='training data end date')
    parser.add_argument('--online_training', action='store_true',
                        help='the train master run for online training')
    parser.add_argument('--shuffle_data_block', action='store_true',
                        help='shuffle the data block or not')
    parser.add_argument('--epoch_num', type=int, default=1,
                        help='number of epoch for training, not '\
                             'support in online training')
    FLAGS = parser.parse_args()

    start_date = int(FLAGS.start_date) if FLAGS.start_date else None
    end_date = int(FLAGS.end_date) if FLAGS.end_date else None
    leader_tm = LeaderTrainerMaster(FLAGS.application_id, FLAGS.data_source,
                                    start_date, end_date,
                                    FLAGS.online_training,
                                    FLAGS.shuffle_data_block,
                                    FLAGS.epoch_num)
    leader_tm.run(listen_port=FLAGS.port)

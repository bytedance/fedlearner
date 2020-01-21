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
from trainer_master import TrainerMaster
from data.data_block_queue import DataBlockQueue
from data.data_source_reader import DataSourceReader


class LeaderTrainerMaster(TrainerMaster):
    def __init__(self, application_id, data_source_reader_):
        super(LeaderTrainerMaster, self).__init__(application_id)
        self._data_block_queue = DataBlockQueue()
        self._data_source_reader = data_source_reader_

    def _load_data(self):
        checkpoint = self._get_checkpoint()
        for data_block in self._data_source_reader.list_data_block():
            if data_block.block_id not in checkpoint:
                self._data_block_queue.put(data_block)

    def _alloc_data_block(self, block_id=None):
        # block_id is unused in leader role
        data_blocks_resp = None
        if not self._data_block_queue.empty():
            data_blocks_resp = self._data_block_queue.get()
        return data_blocks_resp


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser('leader trainer master cmd.')
    parser.add_argument('-p', '--port', type=int, default=50001,
                        help='Listen port of leader trainer master')
    parser.add_argument('-app_id', '--application_id',
                        required=True, help='application_id')
    parser.add_argument('-data_path', '--data_path',
                        required=True, help='training example data path')
    parser.add_argument('-start_date', '--start_date',
                        default=None, help='training data start date')
    parser.add_argument('-end_date', '--end_date',
                        default=None, help='training data end date')
    FLAGS = parser.parse_args()

    data_source_reader = DataSourceReader(
        FLAGS.data_path, FLAGS.start_date, FLAGS.end_date)
    leader_tm = LeaderTrainerMaster(FLAGS.application_id, data_source_reader)
    leader_tm.run(listen_port=FLAGS.port)

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

from fedlearner.data_join.data_block_visitor import DataBlockVisitor
from fedlearner.data_join.common import get_kvstore_config
from .trainer_master import TrainerMaster

kvstore_type = os.environ.get('KVSTORE_TYPE', 'etcd')
db_database, db_addr, db_username, db_password, db_base_dir = \
    get_kvstore_config(kvstore_type)



class FollowerTrainerMaster(TrainerMaster):
    def __init__(self, application_id, data_source,
                 start_time, end_time, online_training):
        super(FollowerTrainerMaster, self).__init__(application_id,
                                                    None, online_training)
        kvstore_use_mock = os.environ.get('KVSTORE_USE_MOCK', "off") == "on"
        self._data_block_visitor = DataBlockVisitor(
            data_source, db_database, db_base_dir, db_addr,
                db_username, db_password, kvstore_use_mock)
        self._start_time = start_time
        self._end_time = end_time

    def _load_data(self):
        pass

    def _alloc_data_block(self, block_id=None):
        logging.debug("FollowerTrainerMaster is getting block %s", block_id)
        if not block_id:
            raise Exception('follower tm need block_id to alloc.')

        return self._data_block_visitor.LoadDataBlockRepByBlockId(block_id)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser('follower trainer master cmd.')
    parser.add_argument('-p',
                        '--port',
                        type=int,
                        default=50002,
                        help='Listen port of follower trainer master')
    parser.add_argument('-app_id',
                        '--application_id',
                        required=True,
                        help='application_id')
    parser.add_argument('-data_source',
                        '--data_source',
                        required=True,
                        help='training example data source')
    parser.add_argument('-start_date',
                        '--start_date',
                        default=None,
                        help='training data start date')
    parser.add_argument('-end_date',
                        '--end_date',
                        default=None,
                        help='training data end date')
    parser.add_argument('--online_training',
                        action='store_true',
                        help='the train master run for online training')

    FLAGS = parser.parse_args()
    start_date = int(FLAGS.start_date) if FLAGS.start_date else None
    end_date = int(FLAGS.end_date) if FLAGS.end_date else None
    follower_tm = FollowerTrainerMaster(
        FLAGS.application_id, FLAGS.data_source,
        start_date, end_date,
        FLAGS.online_training)
    follower_tm.run(listen_port=FLAGS.port)

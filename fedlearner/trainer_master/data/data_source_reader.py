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

import os
import logging
import tensorflow as tf
from .data_block import DataBlock


class DataSourceReader(object):
    def __init__(self, data_source, start_date, end_date):
        self._data_source = data_source
        self._start_date = start_date
        self._end_date = end_date

    def list_data_block(self):
        response = []
        # TODO data_source temporarily is equal to data_path
        # just list all data_block
        if tf.io.gfile.isdir(self._data_source):
            walk = tf.io.gfile.walk(self._data_source)
            for path, dir_list, file_list in walk:
                for file_name in file_list:
                    if '.tfrecord' in file_name:
                        block_id = file_name[:-9]
                        # block_id = '{}_{}'.format(os.path.basename(path),
                        #                           file_name[:-9])
                        data_path = os.path.join(path, file_name)
                        response.append(DataBlock(block_id, data_path, 'meta'))
                        logging.debug(
                            'read data block [block_id:%s, path:%s]',
                            block_id, data_path)
        return response

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

import logging
from contextlib import contextmanager

import tensorflow.compat.v1 as tf

DataBlockSuffix = '.data'
DataBlockMetaSuffix = '.meta'
ExampleIdSuffix = '.done'
RawDataIndexSuffix = '.idx'
RawDataUnIndexSuffix = '.rd'
RawDataTmpSuffix = '.tmp'
InvalidExampleId = ''
InvalidEventTime = -9223372036854775808

@contextmanager
def make_tf_record_iter(fpath):
    record_iter = None
    expt = None
    try:
        record_iter = tf.io.tf_record_iterator(fpath)
        yield record_iter
    except Exception as e: # pylint: disable=broad-except
        logging.warning("Failed make tf_record_iterator for "\
                        "%s, reason %s", fpath, e)
        expt = e
    if record_iter is not None:
        del record_iter
    if expt is not None:
        raise expt

def encode_data_block_meta_fname(data_block_index):
    return '{}{}'.format(data_block_index, DataBlockMetaSuffix)

def encode_data_block_id(start_time, end_time, data_block_index):
    return '{}-{}_{}'.format(start_time, end_time, data_block_index)

def encode_data_block_fname(start_time, end_time, data_block_index):
    data_block_id = encode_data_block_id(
            start_time, end_time, data_block_index
        )
    return '{}{}'.format(data_block_id, DataBlockSuffix)

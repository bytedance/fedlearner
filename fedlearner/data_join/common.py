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
from contextlib import contextmanager

import tensorflow.compat.v1 as tf
from google.protobuf import text_format
from tensorflow.compat.v1 import gfile

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb

DataBlockSuffix = '.data'
DataBlockMetaSuffix = '.meta'
ExampleIdSuffix = '.done'
RawDataMetaPrefix = 'raw_data_'
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

def partition_repr(partition_id):
    return 'partition_{:04}'.format(partition_id)

def encode_data_block_meta_fname(data_source_name,
                                 partition_id,
                                 data_block_index):
    return '{}.{}.{:08}{}'.format(
            data_source_name, partition_repr(partition_id),
            data_block_index, DataBlockMetaSuffix
        )

def encode_block_id(data_source_name, meta):
    return '{}.{}.{:08}.{}-{}'.format(
            data_source_name, partition_repr(meta.partition_id),
            meta.data_block_index, meta.start_time, meta.end_time
        )

def decode_block_id(block_id):
    segs = block_id.split('.')
    if len(segs) != 4:
        raise ValueError("{} invalid. Segmenet of block_id split "\
                          "by . shoud be 4".format(block_id))
    data_source_name = segs[0]
    partition_id = int(segs[1][len('partition_'):])
    data_block_index = int(segs[2])
    time_frame_segs = segs[3].split('-')
    if len(time_frame_segs) != 2:
        raise ValueError("{} invalid. Segmenet of time frame split "
                         "by - should be 2".format(block_id))
    start_time, end_time = int(time_frame_segs[0]), int(time_frame_segs[1])
    return {"data_source_name": data_source_name,
            "partition_id": partition_id,
            "data_block_index": data_block_index,
            "time_frame": (start_time, end_time)}

def encode_data_block_fname(data_source_name, meta):
    block_id = encode_block_id(data_source_name, meta)
    return '{}{}'.format(block_id, DataBlockSuffix)

def load_data_block_meta(meta_fpath):
    assert meta_fpath.endswith(DataBlockMetaSuffix)
    if not gfile.Exists(meta_fpath):
        return None
    with make_tf_record_iter(meta_fpath) as fitr:
        return text_format.Parse(next(fitr).decode(), dj_pb.DataBlockMeta())

def retrieve_data_source(etcd, data_source_name):
    etcd_key = os.path.join(data_source_name, 'master')
    raw_data = etcd.get_data(etcd_key)
    if raw_data is None:
        raise ValueError("etcd master key is None for {}".format(
            data_source_name)
        )
    return text_format.Parse(raw_data, common_pb.DataSource())

def commit_data_source(etcd, data_source):
    etcd_key = os.path.join(data_source.data_source_meta.name, 'master')
    etcd.set_data(etcd_key, text_format.MessageToString(data_source))

def partition_manifest_etcd_key(data_source_name, partition_id):
    return '/'.join([data_source_name, 'raw_data_dir',
                     partition_repr(partition_id)])

def raw_data_meta_etcd_key(data_source_name, partition_id, process_index):
    manifest_etcd_key = \
            partition_manifest_etcd_key(data_source_name, partition_id)
    return '/'.join([manifest_etcd_key,
                     '{}{:08}'.format(RawDataMetaPrefix, process_index)])

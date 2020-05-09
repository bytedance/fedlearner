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
from datetime import datetime

import tensorflow.compat.v1 as tf
from google.protobuf import text_format, timestamp_pb2
from tensorflow.compat.v1 import gfile

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb

DataBlockSuffix = '.data'
DataBlockMetaSuffix = '.meta'
ExampleIdSuffix = '.done'
RawDataMetaPrefix = 'raw_data_'
MergedSortRunSuffix = '.merged'
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

def encode_portal_hourly_dir(base_dir, date_time):
    assert isinstance(date_time, datetime)
    return os.path.join(base_dir, '{}{:02}{:02}'.format(
                        date_time.year, date_time.month, date_time.day),
                        '{:02}'.format(date_time.hour))

def encode_portal_hourly_fpath(base_dir, date_time, partition_id):
    return os.path.join(encode_portal_hourly_dir(base_dir, date_time),
                        'part-r-{:05}.gz'.format(partition_id))

def encode_portal_hourly_finish_tag(base_dir, date_time):
    return os.path.join(encode_portal_hourly_dir(base_dir, date_time),
                        '_SUCCESS')

def retrieve_portal_manifest(etcd, portal_name):
    etcd_key = os.path.join(portal_name, 'manifest')
    raw_data = etcd.get_data(etcd_key)
    if raw_data is None:
        raise ValueError("the manifest of {} should be stored "\
                         "in etcd".format(portal_name))
    return text_format.Parse(raw_data, common_pb.DataJoinPortalManifest())

def commit_portal_manifest(etcd, portal_manifest):
    etcd_key = os.path.join(portal_manifest.name, 'manifest')
    etcd.set_data(etcd_key, text_format.MessageToString(portal_manifest))

def convert_datetime_to_timestamp(date_time):
    assert isinstance(date_time, datetime)
    return timestamp_pb2.Timestamp(
            nanos=0,
            seconds=int((date_time - datetime.fromtimestamp(0)).total_seconds())
        )

def trim_timestamp_by_hourly(timestamp):
    if timestamp.nanos == 0 and timestamp.seconds % 3600 == 0:
        return timestamp
    return timestamp_pb2.Timestamp(
                nanos=0,
                seconds=timestamp.seconds-timestamp.seconds%3600
            )

def convert_timestamp_to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp.seconds + timestamp.nanos/1e9)

def encode_merged_sort_run_fname(partition_id):
    return 'part-{:04}-sort_run{}'.format(partition_id,
                                          MergedSortRunSuffix)

_valid_basic_feature_type = (int, str, bytes, float)
def convert_dict_to_tf_example(src_dict):
    assert isinstance(src_dict, dict)
    tf_feature = {}
    for key, feature in src_dict.items():
        if not isinstance(key, str):
            raise RuntimeError('the key {}({}) of dict must a '\
                               'string'.format(key, type(key)))
        basic_type = type(feature)
        if isinstance(type(feature), list):
            if len(feature) == 0:
                logging.debug('skip %s since feature is empty list', key)
                continue
            basic_type = feature[0]
            if not all(isinstance(x, basic_type) for x in feature):
                raise RuntimeError('type of elements in feature of key {} '\
                                   'is not the same'.format(key))
        if isinstance(feature, _valid_basic_feature_type):
            raise RuntimeError("feature type({}) of key {} is not support "\
                               "for tf Example".format(basic_type, key))
        if basic_type == int:
            value = feature if isinstance(feature, list) else [feature]
            tf_feature[key] = tf.train.Feature(
                int64_list=tf.train.Int64List(value=value))
        elif basic_type == bytes:
            value = feature if isinstance(feature, list) else [feature]
            tf_feature[key] = tf.train.Feature(
                bytes_list=tf.train.BytesList(value=value))
        elif basic_type == str:
            value = [feat.encode() for feat in feature] if \
                     isinstance(feature, list) else [feature.encode()]
            tf_feature[key] = tf.train.Feature(
                bytes_list=tf.train.BytesList(value=value))
        else:
            assert basic_type == float
            value = feature if  isinstance(feature, list) else [feature]
            tf_feature[key] = tf.train.Feature(
                float_list=tf.train.FloatList(value=value))
    return tf.train.Example(features=tf.train.Features(feature=tf_feature))

def convert_tf_example_to_dict(src_tf_example):
    assert isinstance(src_tf_example, tf.train.Example)
    dst_dict = {}
    tf_feature = src_tf_example.features.feature
    for key, feat in tf_feature:
        dst_dict[key] = feat
    return dst_dict

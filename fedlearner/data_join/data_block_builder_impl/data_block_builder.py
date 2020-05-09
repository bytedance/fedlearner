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

import uuid
from os import path

import tensorflow.compat.v1 as tf
from google.protobuf import text_format
from tensorflow.compat.v1 import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join.common import (
    encode_data_block_meta_fname, encode_block_id,
    encode_data_block_fname, partition_repr
)

class DataBlockBuilder(object):
    TMP_COUNTER = 0
    def __init__(self, dirname, data_source_name, partition_id,
                 data_block_index, max_example_num=None):
        self._data_source_name = data_source_name
        self._partition_id = partition_id
        self._max_example_num = max_example_num
        self._dirname = dirname
        self._tmp_fpath = self._get_tmp_fpath()
        self._writer = self._make_data_block_writer(self._tmp_fpath)
        self._data_block_meta = dj_pb.DataBlockMeta()
        self._data_block_meta.partition_id = partition_id
        self._data_block_meta.data_block_index = data_block_index
        self._data_block_meta.follower_restart_index = 0
        self._example_num = 0
        self._data_block_manager = None

    def init_by_meta(self, meta):
        self._partition_id = meta.partition_id
        self._max_example_num = None
        self._data_block_meta = meta

    @classmethod
    def name(cls):
        return 'DATABLOCK_BUILDER'

    def set_data_block_manager(self, data_block_manager):
        self._data_block_manager = data_block_manager

    def append_item(self, item, example_id, event_time,
                    leader_index, follower_index):
        record = self._extract_record_from_item(item)
        self.append_record(record, example_id, event_time,
                           leader_index, follower_index)

    def append_record(self, record, example_id, event_time,
                      leader_index, follower_index):
        self._data_block_meta.example_ids.append(example_id)
        if self._example_num == 0:
            self._data_block_meta.leader_start_index = leader_index
            self._data_block_meta.leader_end_index = leader_index
            self._data_block_meta.start_time = event_time
            self._data_block_meta.end_time = event_time
        else:
            assert self._data_block_meta.leader_start_index < leader_index, \
                "leader start index should be incremental"
            assert self._data_block_meta.leader_end_index < leader_index, \
                "leader end index should be incremental"
            self._data_block_meta.leader_end_index = leader_index
            if event_time < self._data_block_meta.start_time:
                self._data_block_meta.start_time = event_time
            if event_time > self._data_block_meta.end_time:
                self._data_block_meta.end_time = event_time
        self._write_one(record)

    def set_follower_restart_index(self, follower_restart_index):
        self._data_block_meta.follower_restart_index = follower_restart_index

    def write_item(self, item):
        record = self._extract_record_from_item(item)
        self._write_one(record)

    def _write_one(self, record):
        self._write_record(record)
        self._example_num += 1

    def check_data_block_full(self):
        if (self._max_example_num is not None and
                len(self._data_block_meta.example_ids) >=
                        self._max_example_num):
            return True
        return False

    def get_data_block_meta(self):
        if len(self._data_block_meta.example_ids) > 0:
            return self._data_block_meta
        return None

    def get_leader_begin_index(self):
        return self._leader_begin_index

    def example_count(self):
        return len(self._data_block_meta.example_ids)

    def finish_data_block(self):
        assert self._example_num == len(self._data_block_meta.example_ids)
        self._writer.close()
        if len(self._data_block_meta.example_ids) > 0:
            self._data_block_meta.block_id = \
                    encode_block_id(self._data_source_name,
                                         self._data_block_meta)
            data_block_path = path.join(
                    self._get_data_block_dir(),
                    encode_data_block_fname(
                        self._data_source_name,
                        self._data_block_meta
                    )
                )
            gfile.Rename(self._tmp_fpath, data_block_path, True)
            self._build_data_block_meta()
            return self._data_block_meta
        gfile.Remove(self._tmp_fpath)
        return None

    def _extract_record_from_item(self, item):
        raise NotImplementedError('_extract_record_from_item is not '\
                                  'implemented in basic DATABLOCK_BUILDER')

    def _make_data_block_writer(self, fpath):
        raise NotImplementedError('_make_data_block_writer is not '\
                                  'implemented in basic DATABLOCK_BUILDER')

    def _write_record(self, record):
        raise NotImplementedError('_write_record is not implemented '\
                                  'in basic DATABLOCK_BUILDER')

    def _get_data_block_dir(self):
        return path.join(self._dirname,
                         partition_repr(self._partition_id))

    def _get_tmp_fpath(self):
        tmp_fname = str(uuid.uuid1()) + '-{}.tmp'.format(self.TMP_COUNTER)
        self.TMP_COUNTER += 1
        return path.join(self._get_data_block_dir(), tmp_fname)

    def _build_data_block_meta(self):
        tmp_meta_fpath = self._get_tmp_fpath()
        meta = self._data_block_meta
        with tf.io.TFRecordWriter(tmp_meta_fpath) as meta_writer:
            meta_writer.write(text_format.MessageToString(meta).encode())
        if self._data_block_manager is not None:
            self._data_block_manager.commit_data_block_meta(
                    tmp_meta_fpath, meta
                )
        else:
            meta_fname = encode_data_block_meta_fname(self._data_source_name,
                                                      self._partition_id,
                                                      meta.data_block_index)
            meta_fpath = path.join(self._get_data_block_dir(), meta_fname)
            gfile.Rename(tmp_meta_fpath, meta_fpath)

    def __del__(self):
        if self._writer is not None:
            del self._writer

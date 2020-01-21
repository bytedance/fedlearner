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

import threading
import logging
import os
import uuid
import ntpath

import tensorflow as tf
from tensorflow.python.platform import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join.common import (
    DataBlockSuffix, DataBlockMetaSuffix, make_tf_record_iter
)

class DataBlockBuilder(object):
    TMP_COUNTER = 0
    def __init__(self, dirname, partition_id,
                 data_block_index, max_example_num=None):
        self._start_time = None
        self._end_time = None
        self._partition_id = partition_id
        self._max_example_num = max_example_num
        self._dirname = dirname
        self._tmp_fpath = self._get_tmp_fpath()
        self._tf_record_writer = tf.io.TFRecordWriter(self._tmp_fpath)
        self._data_block_meta = dj_pb.DataBlockMeta()
        self._data_block_meta.partition_id = partition_id
        self._data_block_meta.data_block_index = data_block_index
        self._data_block_meta.follower_restart_index = 0
        self._filled = False
        self._example_num = 0

    def init_by_meta(self, meta):
        self._start_time = meta.start_time
        self._end_time = meta.end_time
        self._partition_id = meta.partition_id
        self._max_example_num = None
        self._data_block_meta = meta

    def append(self, record, example_id, event_time,
               leader_index, follower_index):
        if self._start_time is None or self._start_time > event_time:
            self._start_time = event_time
        if self._end_time is None or self._end_time < event_time:
            self._end_time = event_time
        self._tf_record_writer.write(record)
        self._data_block_meta.example_ids.append(example_id)
        if not self._filled:
            self._data_block_meta.leader_start_index = leader_index
            self._data_block_meta.leader_end_index = leader_index
        else:
            assert self._data_block_meta.leader_start_index < leader_index
            assert self._data_block_meta.leader_end_index < leader_index
            self._data_block_meta.leader_end_index = leader_index

        self._filled = True
        self._example_num += 1

    def set_follower_restart_index(self, follower_restart_index):
        self._data_block_meta.follower_restart_index = follower_restart_index

    def append_raw_example(self, record):
        self._tf_record_writer.write(record)
        self._example_num += 1
        self._filled = True

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

    def example_number(self):
        return len(self._data_block_meta.example_ids)

    def finish_data_block(self):
        assert self._example_num == len(self._data_block_meta.example_ids)
        self._tf_record_writer.close()
        self._tf_record_writer = None
        if len(self._data_block_meta.example_ids) > 0:
            data_block_id = self._generate_data_block_id()
            data_block_path = os.path.join(self._get_data_block_dir(),
                                           data_block_id+DataBlockSuffix)
            gfile.Rename(self._tmp_fpath, data_block_path)
            self._data_block_meta.start_time = self._start_time
            self._data_block_meta.end_time = self._end_time
            self._data_block_meta.block_id = data_block_id
            meta_tmp_fpath = self._get_tmp_fpath()
            with tf.io.TFRecordWriter(meta_tmp_fpath) as meta_writer:
                meta_writer.write(self._data_block_meta.SerializeToString())
            meta_path = os.path.join(self._get_data_block_dir(),
                                     data_block_id+DataBlockMetaSuffix)
            gfile.Rename(meta_tmp_fpath, meta_path)
        else:
            gfile.Remove(self._tmp_fpath)

    def _get_data_block_dir(self):
        partition_str = 'partition_{}'.format(self._partition_id)
        return os.path.join(self._dirname, partition_str)

    def _get_tmp_fpath(self):
        tmp_fname = str(uuid.uuid1()) + '-{}.tmp'.format(self.TMP_COUNTER)
        self.TMP_COUNTER += 1
        return os.path.join(self._get_data_block_dir(), tmp_fname)

    def _generate_data_block_id(self):
        return '{}-{}_{}'.format(self._start_time, self._end_time,
                                 self._data_block_meta.data_block_index)

    def __del__(self):
        if self._tf_record_writer is not None:
            self._tf_record_writer.close()
        self._tf_record_writer = None

class DataBlockManager(object):
    def __init__(self, data_source, partition_id):
        self._lock = threading.Lock()
        self._data_source = data_source
        self._partition_id = partition_id
        self._dumped_data_block_meta = []
        self._sync_dumped_data_block_meta()
        self._join_finisehed = False

    def get_dumped_data_block_num(self, force_sync=False):
        if force_sync:
            self._sync_dumped_data_block_meta()
        with self._lock:
            return len(self._dumped_data_block_meta)

    def get_data_block_meta_by_index(self, index, force_sync=False):
        if force_sync:
            self._sync_dumped_data_block_meta()
        with self._lock:
            if index >= len(self._dumped_data_block_meta):
                return None, self._join_finisehed
            return self._dumped_data_block_meta[index], False

    def get_last_data_block_meta(self, force_sync=False):
        if force_sync:
            self._sync_dumped_data_block_meta()
        with self._lock:
            if len(self._dumped_data_block_meta) == 0:
                return None
            return self._dumped_data_block_meta[-1]

    def finish_join(self):
        with self._lock:
            self._join_finisehed = True

    def join_finished(self):
        with self._lock:
            return self._join_finisehed

    def add_dumped_data_block_meta(self, meta, force_sync=False):
        if force_sync:
            self._sync_dumped_data_block_meta()
        with self._lock:
            if meta.data_block_index != len(self._dumped_data_block_meta):
                raise RuntimeError("the new add data block index is "\
                                   "not consecutive")
            if len(self._dumped_data_block_meta) > 0:
                prev_meta = self._dumped_data_block_meta[-1]
                if (prev_meta.follower_restart_index >
                        meta.follower_restart_index):
                    raise RuntimeError(
                            "follower_restart_index is not Incremental"
                        )
                if (prev_meta.leader_start_index >=
                        meta.leader_start_index):
                    raise RuntimeError(
                            "leader_start_index is not Incremental"
                        )
                if (prev_meta.leader_end_index >=
                        meta.leader_end_index):
                    raise RuntimeError(
                            "leader_end_index is not Incremental"
                        )
            self._dumped_data_block_meta.append(meta)

    def _sync_dumped_data_block_meta(self):
        dumped_data_block_path = {}
        dumped_data_block_meta_path = {}
        dumped_data_block_meta = []
        data_block_dir = self._data_block_dir()
        if not gfile.Exists(data_block_dir):
            gfile.MakeDirs(data_block_dir)
        elif not gfile.IsDirectory(data_block_dir):
            logging.fatal("%s must be the directory of data block for "\
                          "partition %d", data_block_dir, self._partition_id)
            os._exit(-1) # pylint: disable=protected-access
        for fpath in self._list_data_block_dir():
            fname = ntpath.basename(fpath)
            if fname.endswith(DataBlockSuffix):
                ftag = fname[:-len(DataBlockSuffix)]
                dumped_data_block_path[ftag] = fpath
            elif fname.endswith(DataBlockMetaSuffix):
                ftag = fname[:-len(DataBlockMetaSuffix)]
                dumped_data_block_meta_path[ftag] = fpath
            else:
                gfile.Remove(fpath)
        for (ftag, fpath) in dumped_data_block_meta_path.items():
            if ftag not in dumped_data_block_path:
                gfile.Remove(fpath)
                gfile.Remove(dumped_data_block_path[ftag])
            else:
                with make_tf_record_iter(fpath) as record_iter:
                    dbm = dj_pb.DataBlockMeta()
                    dbm.ParseFromString(next(record_iter))
                    dumped_data_block_meta.append(dbm)
        dumped_data_block_meta = sorted(
                dumped_data_block_meta, key=lambda meta: meta.data_block_index
            )
        for (idx, meta) in enumerate(dumped_data_block_meta):
            if meta.data_block_index != idx:
                logging.fatal("data_block_index is not consecutive")
                os._exit(-1) # pylint: disable=protected-access
            if idx == 0:
                continue
            prev_meta = dumped_data_block_meta[idx-1]
            if prev_meta.follower_restart_index > meta.follower_restart_index:
                logging.fatal("follower_restart_index is not Incremental")
                os._exit(-1) # pylint: disable=protected-access
            if prev_meta.leader_start_index >= meta.leader_start_index:
                logging.fatal("leader_start_index is not Incremental")
                os._exit(-1) # pylint: disable=protected-access
            if prev_meta.leader_end_index >= meta.leader_end_index:
                logging.fatal("leader_end_index is not Incremental")
                os._exit(-1) # pylint: disable=protected-access
        with self._lock:
            if len(dumped_data_block_meta) > len(self._dumped_data_block_meta):
                self._dumped_data_block_meta = dumped_data_block_meta

    def _list_data_block_dir(self):
        data_block_dir = self._data_block_dir()
        fpaths = [os.path.join(data_block_dir, f)
                    for f in gfile.ListDirectory(data_block_dir)
                    if not gfile.IsDirectory(os.path.join(data_block_dir, f))]
        fpaths.sort()
        return fpaths

    def _data_block_dir(self):
        return os.path.join(self._data_source.data_block_dir,
                            'partition_{}'.format(self._partition_id))

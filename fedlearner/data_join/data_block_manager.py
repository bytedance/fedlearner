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

import copy
import logging
import os
import threading
import traceback

import tensorflow.compat.v1 as tf
from google.protobuf import text_format
from tensorflow.compat.v1 import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import metrics
from fedlearner.data_join.common import (
    encode_data_block_meta_fname, partition_repr,
    load_data_block_meta, encode_block_id,
    encode_data_block_fname, gen_tmp_fpath,
    data_source_data_block_dir
)
from fedlearner.data_join.output_writer_impl import create_output_writer


class DataBlockBuilder(object):
    def __init__(self, dirname, data_source_name, partition_id,
                 data_block_index, write_options, max_example_num=None):
        self._data_source_name = data_source_name
        self._partition_id = partition_id
        self._max_example_num = max_example_num
        self._dirname = dirname
        self._tmp_fpath = self._get_tmp_fpath()
        self._writer = create_output_writer(write_options, self._tmp_fpath)
        self._data_block_meta = dj_pb.DataBlockMeta()
        self._data_block_meta.partition_id = partition_id
        self._data_block_meta.data_block_index = data_block_index
        self._data_block_meta.follower_restart_index = 0
        self._example_num = 0
        self._data_block_manager = None
        self._example_ids_size = 0
        self._metrics_tags = {'data_source_name': self._data_source_name,
                              'partition': partition_id}

    def init_by_meta(self, meta):
        self._partition_id = meta.partition_id
        self._max_example_num = None
        self._data_block_meta = meta

    def set_data_block_manager(self, data_block_manager):
        self._data_block_manager = data_block_manager

    def append_item(self, item, leader_index, follower_index, event_time=None,\
                    allow_dup=False, joined=-1):
        example_id = item.example_id
        if event_time is None:
            event_time = item.event_time
        self._data_block_meta.example_ids.append(example_id)
        if hasattr(item, 'id_type'):
            # v2
            self._data_block_meta.indices.append(leader_index)
        #write joined to leader
        if joined != -1:
            self._data_block_meta.joined.append(joined)
        self._example_ids_size += len(example_id)
        if self._example_num == 0:
            self._data_block_meta.leader_start_index = leader_index
            self._data_block_meta.leader_end_index = leader_index
            self._data_block_meta.start_time = event_time
            self._data_block_meta.end_time = event_time
        else:
            if not allow_dup:
                assert self._data_block_meta.leader_start_index < leader_index,\
                        "leader start index should be incremental"
                assert self._data_block_meta.leader_end_index < leader_index, \
                        "leader end index should be incremental"
            else:
                assert self._data_block_meta.leader_start_index <= \
                        leader_index,\
                        "leader start index should be incremental by GE"
                assert self._data_block_meta.leader_end_index <= leader_index, \
                    "leader end index should be incremental by LE"

            self._data_block_meta.leader_end_index = leader_index
            if event_time < self._data_block_meta.start_time:
                self._data_block_meta.start_time = event_time
            if event_time > self._data_block_meta.end_time:
                self._data_block_meta.end_time = event_time
        # write joined to follower
        if joined != -1:
            item.add_extra_fields({'joined': joined})
        self.write_item(item)

    def set_follower_restart_index(self, follower_restart_index):
        self._data_block_meta.follower_restart_index = follower_restart_index

    def write_item(self, item):
        self._writer.write_item(item)
        self._example_num += 1

    def check_data_block_full(self):
        if self._example_ids_size >= 3 << 20:
            logging.info("DataBlock full since data block "\
                         "meta maybe large than 3MB")
            return True
        if self._max_example_num is not None and \
                len(self._data_block_meta.example_ids) >= \
                self._max_example_num:
            logging.info("DataBlock full since reach to max_"\
                         "example_num %d", self._max_example_num)
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

    def set_join_stats_info(self, join_stats_info):
        self._data_block_meta.joiner_stats_info.MergeFrom(join_stats_info)

    def finish_data_block(self, emit_logger=False, metrics_tags=None):
        assert self._example_num == len(self._data_block_meta.example_ids)
        self._writer.close()
        if len(self._data_block_meta.example_ids) > 0:
            self._data_block_meta.block_id = \
                    encode_block_id(self._data_source_name,
                                         self._data_block_meta)
            data_block_path = os.path.join(
                    self._get_data_block_dir(),
                    encode_data_block_fname(
                        self._data_source_name,
                        self._data_block_meta
                    )
                )
            gfile.Rename(self._tmp_fpath, data_block_path, True)
            self._build_data_block_meta()
            if emit_logger:
                self._emit_logger(metrics_tags)
            return self._data_block_meta
        gfile.Remove(self._tmp_fpath)
        return None

    def _emit_logger(self, metrics_tags):
        meta = self._data_block_meta
        nmetric_tags = self._metrics_tags
        if metrics_tags is not None and len(metrics_tags) > 0:
            nmetric_tags = copy.deepcopy(self._metrics_tags)
            nmetric_tags.update(metrics_tags)
        metrics.emit_store(name='data_block_index',
                           value=meta.data_block_index,
                           tags=nmetric_tags)
        metrics.emit_store(name='stats_cum_join_num',
                           value=meta.joiner_stats_info.stats_cum_join_num,
                           tags=nmetric_tags)
        metrics.emit_store(name='actual_cum_join_num',
                           value=meta.joiner_stats_info.actual_cum_join_num,
                           tags=nmetric_tags)
        metrics.emit_store(name='leader_stats_index',
                           value=meta.joiner_stats_info.leader_stats_index,
                           tags=nmetric_tags)
        metrics.emit_store(name='follower_stats_index',
                           value=meta.joiner_stats_info.follower_stats_index,
                           tags=nmetric_tags)
        leader_join_rate = 0.0
        if meta.joiner_stats_info.leader_stats_index > 0:
            leader_join_rate = meta.joiner_stats_info.actual_cum_join_num / \
                    meta.joiner_stats_info.leader_stats_index
        follower_join_rate = 0.0
        if meta.joiner_stats_info.follower_stats_index > 0:
            follower_join_rate = meta.joiner_stats_info.actual_cum_join_num / \
                meta.joiner_stats_info.follower_stats_index
        metrics.emit_store(name='leader_join_rate_percent',
                           value=int(leader_join_rate*100),
                           tags=nmetric_tags)
        metrics.emit_store(name='follower_join_rate_percent',
                           value=int(follower_join_rate*100),
                           tags=nmetric_tags)
        logging.info("create new data block id: %s, data block index: %d," \
                     "stats:\n stats_cum_join_num: %d, actual_cum_join_num: "\
                     "%d, leader_stats_index: %d, follower_stats_index: %d, "\
                     "leader_join_rate: %f, follower_join_rate: %f",
                     meta.block_id, meta.data_block_index,
                     meta.joiner_stats_info.stats_cum_join_num,
                     meta.joiner_stats_info.actual_cum_join_num,
                     meta.joiner_stats_info.leader_stats_index,
                     meta.joiner_stats_info.follower_stats_index,
                     leader_join_rate, follower_join_rate)

    def _get_data_block_dir(self):
        return os.path.join(self._dirname,
                            partition_repr(self._partition_id))

    def _get_tmp_fpath(self):
        return gen_tmp_fpath(self._get_data_block_dir())

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
            meta_fpath = os.path.join(self._get_data_block_dir(), meta_fname)
            gfile.Rename(tmp_meta_fpath, meta_fpath)

    def __del__(self):
        if self._writer is not None:
            del self._writer


class DataBlockManager(object):
    def __init__(self, data_source, partition_id):
        self._lock = threading.Lock()
        self._data_source = data_source
        self._partition_id = partition_id
        self._data_block_meta_cache = {}
        self._dumped_index = None
        self._dumping_index = None
        self._make_directory_if_nessary()
        self._sync_dumped_index()

    def get_dumped_data_block_count(self):
        with self._lock:
            self._sync_dumped_index()
            return self._dumped_index + 1

    def get_data_block_meta_by_index(self, index):
        with self._lock:
            if index < 0:
                raise IndexError("{} index out of range".format(index))
            self._sync_dumped_index()
            return self._sync_data_block_meta(index)

    def get_lastest_data_block_meta(self):
        with self._lock:
            self._sync_dumped_index()
            return self._sync_data_block_meta(self._dumped_index)

    def commit_data_block_meta(self, tmp_meta_fpath, data_block_meta):
        if not gfile.Exists(tmp_meta_fpath):
            raise RuntimeError("the tmp file is not existed {}"\
                               .format(tmp_meta_fpath))
        with self._lock:
            if self._dumping_index is not None:
                raise RuntimeError(
                        "data block with index {} is " \
                        "dumping".format(self._dumping_index)
                    )
            data_block_index = data_block_meta.data_block_index
            if data_block_index != self._dumped_index + 1:
                raise IndexError("the data block index shoud be consecutive")
            self._dumping_index = data_block_index
            meta_fpath = self._get_data_block_meta_path(data_block_index)
            gfile.Rename(tmp_meta_fpath, meta_fpath)
            self._dumping_index = None
            self._dumped_index = data_block_index
            self._evict_data_block_cache_if_full()
            self._data_block_meta_cache[data_block_index] = data_block_meta

    def _sync_dumped_index(self):
        if self._dumped_index is None:
            assert self._dumping_index is None, \
                "no index is dumping when no dumped index"
            left_index = 0
            right_index = 1 << 63
            while left_index <= right_index:
                index = (left_index + right_index) // 2
                fname = self._get_data_block_meta_path(index)
                if gfile.Exists(fname):
                    left_index = index + 1
                else:
                    right_index = index - 1
            self._dumped_index = right_index
        elif self._dumping_index is not None:
            assert self._dumping_index == self._dumped_index + 1, \
                "the dumping index shoud be next of dumped index "\
                "{} != {} + 1".format(self._dumping_index, self._dumped_index)
            fpath = self._get_data_block_meta_path(self._dumping_index)
            if not gfile.Exists(fpath):
                self._dumping_index = None
            else:
                self._dumped_index = self._dumping_index
                self._dumping_index = None

    def _make_directory_if_nessary(self):
        data_block_dir = self._data_block_dir()
        if not gfile.Exists(data_block_dir):
            gfile.MakeDirs(data_block_dir)
        if not gfile.IsDirectory(data_block_dir):
            logging.fatal("%s should be directory", data_block_dir)
            traceback.print_stack()
            os._exit(-1) # pylint: disable=protected-access

    def _sync_data_block_meta(self, index):
        if self._dumped_index < 0 or index > self._dumped_index:
            return None
        if index not in self._data_block_meta_cache:
            self._evict_data_block_cache_if_full()
            fpath = self._get_data_block_meta_path(index)
            meta = load_data_block_meta(fpath)
            if meta is None:
                logging.fatal("data block index as %d has dumped "\
                              "but vanish", index)
                traceback.print_stack()
                os._exit(-1) # pylint: disable=protected-access
            self._data_block_meta_cache[index] = meta
        return self._data_block_meta_cache[index]

    def _get_data_block_meta_path(self, data_block_index):
        meta_fname = encode_data_block_meta_fname(
                self._data_source.data_source_meta.name,
                self._partition_id, data_block_index
            )
        return os.path.join(self._data_block_dir(), meta_fname)

    def _data_block_dir(self):
        return os.path.join(data_source_data_block_dir(self._data_source),
                            partition_repr(self._partition_id))

    def _evict_data_block_cache_if_full(self):
        while len(self._data_block_meta_cache) >= 1024:
            self._data_block_meta_cache.popitem()

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

import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile
from google.protobuf import text_format

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import common_pb2 as common_pb

from fedlearner.common.mysql_client import DBClient
from fedlearner.data_join.common import (
    DataBlockSuffix, encode_data_block_meta_fname,
    load_data_block_meta, encode_data_block_fname,
    decode_block_id, retrieve_data_source, partition_repr,
    partition_manifest_kvstore_key, data_source_data_block_dir
)

class DataBlockRep(object):
    def __init__(self, data_source_name, data_block_fname,
                 partition_id, dirpath, check_existed=True):
        assert data_block_fname.endswith(DataBlockSuffix), \
            "data block fname {} should has suffix {}".format(
                data_block_fname, DataBlockSuffix
            )
        block_id = data_block_fname[:-len(DataBlockSuffix)]
        segmap = decode_block_id(block_id)
        if segmap["data_source_name"] != data_source_name:
            raise ValueError("{} invalid. Data source name mismatch "\
                             "{} != {}".format(data_block_fname,
                                 segmap["data_source_name"], data_source_name))
        self._data_source_name = data_source_name
        if segmap["partition_id"] != partition_id:
            raise ValueError("{} invalid. partition mismatch "\
                             "{} != {}".format(data_block_fname,
                                 segmap["partition_id"], partition_id))
        self._partition_id = partition_id
        start_time, end_time = \
                segmap["time_frame"][0], segmap["time_frame"][1]
        if start_time > end_time:
            raise ValueError("{} invalid. time frame error start_time {} > "\
                             "end_time {}".format(data_block_fname,
                                                  start_time, end_time))
        self._start_time, self._end_time = start_time, end_time
        self._data_block_index = segmap["data_block_index"]
        self._block_id = block_id
        meta_fname = encode_data_block_meta_fname(self._data_source_name,
                                                  self._partition_id,
                                                  self._data_block_index)
        meta_fpath = os.path.join(dirpath, meta_fname)
        if check_existed and (not gfile.Exists(meta_fpath) or \
                              gfile.IsDirectory(meta_fpath)):
            raise ValueError("{} invalid. the corresponding meta file "\
                             "is not existed".format(data_block_fname))
        self._data_block_meta_fpath = meta_fpath
        self._data_block_meta = None
        self._data_block_fpath = os.path.join(dirpath, data_block_fname)

    @property
    def block_id(self):
        return self._block_id

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    @property
    def partition_id(self):
        return self._partition_id

    @property
    def data_block_fpath(self):
        return self._data_block_fpath

    @property
    def data_block_meta(self):
        if self._data_block_meta is None:
            self._data_block_meta = \
                    load_data_block_meta(self._data_block_meta_fpath)
        return self._data_block_meta

    @property
    def data_block_index(self):
        return self._data_block_index

class DataBlockVisitor(object):
    def __init__(self, data_source_name, db_database,
                 db_base_dir, db_addr, db_username,
                 db_password, use_mock_etcd=False):
        self._kvstore = DBClient(db_database, db_addr, db_username,
                                  db_password, db_base_dir,
                                  use_mock_etcd)
        self._data_source = retrieve_data_source(self._kvstore,
                                                 data_source_name)

    def LoadDataBlockRepByTimeFrame(self, start_time=None, end_time=None):
        partition_num = self._data_source.data_source_meta.partition_num
        data_block_fnames = {}
        for partition_id in range(0, partition_num):
            data_block_fnames[partition_id] = \
                self._list_data_block(partition_id)
        data_block_reps = {}
        for partition_id, fnames in data_block_fnames.items():
            manifest = self._sync_raw_data_manifest(partition_id)
            for idx, fname in enumerate(fnames):
                check_existed = (idx == len(fnames) - 1)
                rep = self._make_data_block_rep(partition_id, fname,
                                                check_existed)
                filtered = True
                reason = ''
                if rep is None:
                    reason = 'failed to create data block rep'
                elif end_time is not None and rep.end_time > end_time:
                    reason = 'excess time frame'
                elif start_time is not None and rep.end_time <= start_time:
                    reason = 'less time frame'
                elif self._filter_by_visible(rep.data_block_index, manifest):
                    reason = 'data block visible'
                else:
                    data_block_reps[rep.block_id] = rep
                    filtered = False
                if filtered:
                    logging.debug('skip %s since %s', fname, reason)
        return data_block_reps

    def LoadDataBlockReqByIndex(self, partition_id, data_block_index):
        partition_num = self._data_source.data_source_meta.partition_num
        if partition_id < 0 or partition_id >= partition_num:
            raise IndexError("partition {} out range".format(partition_id))
        dirpath = self._partition_data_block_dir(partition_id)
        meta_fname = encode_data_block_meta_fname(self._data_source_name(),
                                                  partition_id,
                                                  data_block_index)
        meta_fpath = os.path.join(dirpath, meta_fname)
        meta = load_data_block_meta(meta_fpath)
        manifest = self._sync_raw_data_manifest(partition_id)
        if meta is not None and \
                not self._filter_by_visible(meta.data_block_index, manifest):
            fname = encode_data_block_fname(self._data_source_name(), meta)
            return DataBlockRep(self._data_source_name(),
                                fname, partition_id, dirpath)
        return None

    def LoadDataBlockRepByBlockId(self, block_id):
        block_info = decode_block_id(block_id)
        return self.LoadDataBlockReqByIndex(
            block_info['partition_id'], block_info['data_block_index'])

    def _list_data_block(self, partition_id):
        dirpath = self._partition_data_block_dir(partition_id)
        if gfile.Exists(dirpath) and gfile.IsDirectory(dirpath):
            return [f for f in gfile.ListDirectory(dirpath)
                    if f.endswith(DataBlockSuffix)]
        return []

    def _partition_data_block_dir(self, partition_id):
        return os.path.join(data_source_data_block_dir(self._data_source),
                            partition_repr(partition_id))

    def _make_data_block_rep(self, partition_id,
                             data_block_fname, check_existed):
        try:
            rep = DataBlockRep(self._data_source.data_source_meta.name,
                               data_block_fname, partition_id,
                               self._partition_data_block_dir(partition_id),
                               check_existed)
        except Exception as e: # pylint: disable=broad-except
            logging.warning("Failed to create data block rep for %s in"\
                            "partition %d reason %s", data_block_fname,
                            partition_id, e)
            return None
        return rep

    def _data_source_name(self):
        return self._data_source.data_source_meta.name

    def _sync_raw_data_manifest(self, partition_id):
        kvstore_key = partition_manifest_kvstore_key(self._data_source_name(),
                                               partition_id)
        data = self._kvstore.get_data(kvstore_key)
        assert data is not None, "raw data manifest of partition "\
                                 "{} must be existed".format(partition_id)
        return text_format.Parse(data, dj_pb.RawDataManifest())

    def _filter_by_visible(self, index, manifest):
        join_state = manifest.join_example_rep.state
        if self._data_source.role == common_pb.FLRole.Follower and \
                join_state != dj_pb.JoinExampleState.Joined:
            return index > manifest.peer_dumped_index
        return False

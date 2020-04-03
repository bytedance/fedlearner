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

from tensorflow.compat.v1 import gfile

from fedlearner.common.etcd_client import EtcdClient
from fedlearner.data_join.common import (
    DataBlockSuffix, encode_data_block_meta_fname,
    load_data_block_meta, encode_data_block_fname,
    decode_block_id, retrieve_data_source, partition_repr
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
    def __init__(self, data_source_name, etcd_name,
                 etcd_base_dir, etcd_addrs, use_mock_etcd=False):
        etcd = EtcdClient(etcd_name, etcd_addrs, etcd_base_dir, use_mock_etcd)
        self._data_source = retrieve_data_source(etcd, data_source_name)

    def LoadDataBlockRepByTimeFrame(self, start_time, end_time):
        if end_time < self._data_source.data_source_meta.start_time or \
                start_time > self._data_source.data_source_meta.end_time:
            raise ValueError("time frame is out of range")
        partition_num = self._data_source.data_source_meta.partition_num
        data_block_fnames = {}
        for partition_id in range(0, partition_num):
            data_block_fnames[partition_id] = \
                self._list_data_block(partition_id)
        data_block_reps = {}
        for partition_id, fnames in data_block_fnames.items():
            for idx, fname in enumerate(fnames):
                check_existed = (idx == len(fnames) - 1)
                rep = self._make_data_block_rep(partition_id, fname,
                                                check_existed)
                if rep is not None and\
                        not (rep.start_time > end_time or\
                                rep.end_time < start_time):
                    data_block_reps[rep.block_id] = rep
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
        if meta is not None:
            fname = encode_data_block_fname(self._data_source_name(), meta)
            return DataBlockRep(self._data_source_name(),
                                fname, partition_id, dirpath)
        return None

    def _list_data_block(self, partition_id):
        dirpath = self._partition_data_block_dir(partition_id)
        if gfile.Exists(dirpath) and gfile.IsDirectory(dirpath):
            return [f for f in gfile.ListDirectory(dirpath)
                    if f.endswith(DataBlockSuffix)]
        return []

    def _partition_data_block_dir(self, partition_id):
        return os.path.join(self._data_source.data_block_dir,
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

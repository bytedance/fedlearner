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

import bisect
import logging
import os
import threading
import ntpath

from google.protobuf import text_format
from google.protobuf import empty_pb2
from tensorflow.python.platform import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join.raw_data_iter_impl import create_raw_data_iter

class RawDataManager(object):
    def __init__(self, etcd, data_source, partition_id):
        self._lock = threading.Lock()
        self._etcd = etcd
        self._data_source = data_source
        self._partition_id = partition_id
        self._raw_data_reps = {}
        self._process_sequence = []
        self._init_raw_data_reps()

    def get_indexed_raw_data_reps(self):
        reps = []
        with self._lock:
            for fname in self._process_sequence:
                rep = self._sync_raw_data_rep(fname)
                if not rep.HasField('index'):
                    break
                reps.append(rep)
        return reps

    def get_raw_data_rep_by_index(self, index):
        with self._lock:
            if index >= len(self._process_sequence):
                return None
            fname = self._process_sequence[index]
            return self._sync_raw_data_rep(fname)

    def index_raw_data_rep(self, index, start_index):
        with self._lock:
            if index >= len(self._process_sequence):
                raise IndexError("index {} is out of range".format(index))
            unindexed_rep = None
            for (idx, fname) in enumerate(self._process_sequence):
                self._sync_raw_data_rep(fname)
                if idx < index:
                    if not self._raw_data_reps[fname].HasField('index'):
                        raise RuntimeError(
                            "file process before has not been indexed"
                        )
                elif idx == index:
                    meeted = True
                    unindexed_rep = self._raw_data_reps[fname]
                    if unindexed_rep.HasField('index'):
                        raise RuntimeError("{} has been indexed".format(fname))
                    if idx > 0:
                        prev_fname = self._process_sequence[idx-1]
                        prev_rep = self._raw_data_reps[prev_fname]
                        if prev_rep.index.start_index > start_index:
                            raise RuntimeError(
                                    "the start index is not incremental"
                                )
                elif self._raw_data_reps[fname].HasField('index'):
                    raise RuntimeError(
                        "file process after has been indexed"
                    )
            indexed_rep = dj_pb.RawDataRep()
            indexed_rep.raw_data_path = unindexed_rep.raw_data_path
            indexed_rep.index.start_index = start_index
            fname = self._process_sequence[index]
            self._update_raw_data_rep(fname, indexed_rep)

    def _init_raw_data_reps(self):
        existed_rep = set()
        manifest = self._get_manifest()
        self._raw_data_reps = self._get_etcd_raw_data_rep()
        self._process_sequence = list(self._raw_data_reps.keys())
        self._process_sequence.sort()
        last_fname = (None if len(self._process_sequence) == 0
                        else self._process_sequence[-1])
        for fpath in self._list_raw_data_dir():
            fname = ntpath.basename(fpath)
            if (fname in self._raw_data_reps or
                    (last_fname is not None and fname > last_fname)):
                continue
            raw_data_rep = dj_pb.RawDataRep(
                    unindexed=empty_pb2.Empty(),
                    raw_data_path=fpath
                )
            self._update_raw_data_rep(fname, raw_data_rep)
            self._process_sequence.append(fname)
        self._process_sequence.sort()
        meet_unindexed = False
        for fname in self._process_sequence:
            rep = self._raw_data_reps[fname]
            assert rep is not None
            if rep.HasField('unindexed'):
                meet_unindexed = True
            elif meet_unindexed:
                logging.fatal('indexed raw data should be consecutive')
                os._exit(-1) # pylint: disable=protected-access

    def _get_manifest_etcd_key(self):
        return '/'.join([self._data_source.data_source_meta.name,
                        'raw_data_dir',
                        'partition_{}'.format(self._partition_id)])

    def _get_etcd_raw_data_rep(self):
        etcd_prefix = self._get_manifest_etcd_key()
        kvs = self._etcd.get_prefix_kvs(etcd_prefix)
        raw_data_reps = {}
        for (fpath, data) in kvs:
            fname = ntpath.basename(fpath)
            raw_data_reps[fname] = text_format.Parse(data, dj_pb.RawDataRep())
        return raw_data_reps

    def _raw_data_dir(self):
        return os.path.join(self._data_source.raw_data_dir,
                             'partition_{}'.format(self._partition_id))

    def _list_raw_data_dir(self):
        raw_data_dir = self._raw_data_dir()
        fpaths = [os.path.join(raw_data_dir, f)
                    for f in gfile.ListDirectory(raw_data_dir)
                    if not gfile.IsDirectory(os.path.join(raw_data_dir, f))]
        fpaths.sort()
        return fpaths

    def _get_manifest(self):
        manifest_etcd_key = self._get_manifest_etcd_key()
        manifest_data = self._etcd.get_data(manifest_etcd_key)
        if manifest_data is not None:
            return text_format.Parse(manifest_data, dj_pb.RawDataManifest())
        raise RuntimeError(
                "partition id {} has no manifest".format(self._partition_id)
            )

    def _update_raw_data_rep(self, fname, raw_data_rep):
        self._raw_data_reps[fname] = None
        etcd_key = os.path.join(self._get_manifest_etcd_key(), fname)
        self._etcd.set_data(etcd_key, text_format.MessageToString(raw_data_rep))
        self._raw_data_reps[fname] = raw_data_rep

    def _sync_raw_data_rep(self, fname):
        assert fname in self._raw_data_reps
        if self._raw_data_reps[fname] is None:
            fdir = self._get_parition_etcd_key()
            fpath = '/'.join([fdir, fname])
            data = self._etcd.get_data(fpath)
            self._raw_data_reps[fname] = text_format.Parse(
                    data, dj_pb.RawDataRep()
                )
        return self._raw_data_reps[fname]

class RawDataVisitor(object):
    def __init__(self, etcd, data_source, partition_id, options):
        self._raw_data_manager = RawDataManager(etcd, data_source, partition_id)
        self._raw_data_reps = []
        self._raw_data_start_index = []
        self._raw_data_iter = None
        self._finished = False
        self._options = options
        for rep in self._raw_data_manager.get_indexed_raw_data_reps():
            self.append_raw_data_rep(rep)

    def seek(self, target_index):
        self._finished = False
        return self._seek_internal(target_index)

    def get_current_index(self):
        if self._raw_data_iter is None:
            return 0
        return self._raw_data_iter.get_index()

    def finished(self):
        return self._finished

    def reset(self):
        self._finished = False
        self._raw_data_iter = None

    def _seek_internal(self, target_index):
        if (self._raw_data_iter is not None and
                self._raw_data_iter.get_index() == target_index):
            return target_index, self._raw_data_iter.get_item()
        assert len(self._raw_data_reps) == len(self._raw_data_start_index)
        idx = bisect.bisect_left(self._raw_data_start_index, target_index)
        if (len(self._raw_data_reps) > 0 and
                (len(self._raw_data_reps) == idx or
                    self._raw_data_reps[idx].index.start_index > target_index)):
            idx -= 1
            if idx < 0:
                raise IndexError(
                        "target_index {} is too samll".format(target_index)
                    )
        if idx < len(self._raw_data_reps):
            if self._raw_data_iter is None:
                self._raw_data_iter = create_raw_data_iter(
                        self._options, self._options
                    )
            self._raw_data_iter.reset_iter(self._raw_data_reps[idx])
            self._raw_data_iter.seek_to_target(target_index)
            assert self._raw_data_iter.get_index() <= target_index
            if self._raw_data_iter.get_index() == target_index:
                item = self._raw_data_iter.get_item()
                return target_index, item
            idx += 1
            if idx != len(self._raw_data_reps):
                raise IndexError('raw data index is not consecutive')
        next_rep = self._raw_data_manager.get_raw_data_rep_by_index(idx)
        if next_rep is None:
            self._finished = True
            raise StopIteration("all raw data finished")
        if next_rep.HasField('unindexed'):
            start_index = 0
            if self._raw_data_iter is not None:
                start_index = self._raw_data_iter.get_index() + 1
            self._index_raw_data_rep(idx, start_index)
        return self._seek_internal(target_index)

    def __iter__(self):
        return self

    def __next__(self):
        return self._next_internal()

    def next(self):
        return self._next_internal()

    def _next_internal(self):
        try:
            if self._raw_data_iter is None:
                raise StopIteration()
            return next(self._raw_data_iter)
        except StopIteration:
            return self._seek_internal(self._get_next_index())

    def _get_next_index(self):
        if self._raw_data_iter is None:
            return 0
        return self._raw_data_iter.get_index() + 1

    def _append_raw_data_rep(self, rep):
        assert rep.HasField('index')
        assert len(self._raw_data_reps) == len(self._raw_data_start_index)
        if len(self._raw_data_reps) > 0:
            prev_rep = self._raw_data_reps[-1]
            if prev_rep.index.start_index >= rep.index.start_index:
                logging.fatal("index between raw data block %s, %s is "\
                              "not incremental", prev_rep.raw_data_path,
                              rep.raw_data_path)
                os._exit(-1) # pylint: disable=protected-access
        self._raw_data_reps.append(rep)
        self._raw_data_start_index.append(rep.index.start_index)

    def _index_raw_data_rep(self, raw_data_index, start_index):
        self._raw_data_manager.index_raw_data_rep(raw_data_index, start_index)
        index_rep = self._raw_data_manager.get_raw_data_rep_by_index(
            raw_data_index)
        self._append_raw_data_rep(index_rep)

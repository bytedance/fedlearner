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
import os
import ntpath

from google.protobuf import text_format
from google.protobuf import empty_pb2
from tensorflow.python.platform import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join import visitor
from fedlearner.data_join.common import ExampleIdSuffix, make_tf_record_iter
from fedlearner.data_join.raw_data_iter_impl import (
    tf_record_iter, raw_data_iter
)

class ExampleIdManager(visitor.IndexMetaManager):
    def __init__(self, etcd, data_source, partition_id, visit_only):
        self._etcd = etcd
        self._data_source = data_source
        self._partition_id = partition_id
        self._visit_only = visit_only
        self._make_directory_if_nessary()
        super(ExampleIdManager, self).__init__(
                self._example_dumped_dir(), ExampleIdSuffix, visit_only
            )
        self._anchor = None
        self._sync_dumped_example_id_anchor()
        if self._visit_only:
            assert self._anchor is not None
            if self._anchor.HasField('undumped'):
                self._index_metas = []
            else:
                self._index_metas = self._index_metas[:
                        self._anchor.last_meta.process_index+1]

    def get_next_process_index(self):
        with self._lock:
            anchor = self._sync_dumped_example_id_anchor()
            return 0 if self._anchor.HasField('undumped') else \
                    self._anchor.last_meta.process_index + 1

    def get_last_dumped_index(self):
        with self._lock:
            anchor = self._sync_dumped_example_id_anchor()
            assert anchor is not None
            if anchor.HasField('last_meta'):
                return anchor.last_meta.end_index
            return None

    def check_index_meta_by_process_index(self, process_index):
        with self._lock:
            self._sync_dumped_example_id_anchor()
            assert self._anchor is not None
            if self._anchor.HasField('undumped'):
                return False
            dumped_process_index = self._anchor.last_meta.process_index
            return dumped_process_index >= process_index

    def update_dumped_example_id_anchor(self, index_meta, end_index):
        process_index = index_meta.process_index
        start_index = index_meta.start_index
        fpath = index_meta.fpath
        dirname = ntpath.dirname(fpath)
        fname = ntpath.basename(fpath)
        if not gfile.Exists(fpath):
            raise ValueError("file {} is not existed".format(fpath))
        if dirname != self._example_dumped_dir():
            raise ValueError("file {} should be in {}".format(
                             fpath, self._example_dumped_dir()))
        if start_index > end_index:
            raise ValueError("bad index range[{}, {}]".format(
                              start_index, end_index))
        encode_fname = visitor.encode_index_fname(process_index,
                                                  start_index,
                                                  ExampleIdSuffix)
        if encode_fname != fname:
            raise ValueError("encode_fname mismatch {} != {} "\
                             .format(encode_fname, fname))
        with self._lock:
            if self._visit_only:
                raise RuntimeError("update_dumped_example_id_anchor only "\
                                   "support not visit only")
            self._sync_dumped_example_id_anchor()
            if self._anchor.HasField('undumped'):
                if start_index != 0 or process_index != 0:
                    raise ValueError("start index and process index "\
                                     "should start at 0")
            else:
                if start_index <= self._anchor.last_meta.end_index:
                    raise ValueError("index should be incremental")
                if process_index != self._anchor.last_meta.process_index+1:
                    raise ValueError("process index should be consecutive")
            new_anchor = dj_pb.DumpedExampleIdAnchor(
                    last_meta=dj_pb.LastDumpedExampleIdMeta(
                        file_path=fpath,
                        start_index=start_index,
                        end_index=end_index,
                        process_index=process_index
                    )
                )
            self._anchor = None
            etcd_key = self._get_anchor_etcd_key()
            self._etcd.set_data(
                    etcd_key, text_format.MessageToString(new_anchor)
                )
            self._anchor = new_anchor

    def get_example_dumped_dir(self):
        return self._example_dumped_dir()

    def _new_index_meta(self, process_index, start_index):
        if not self._visit_only:
            raise RuntimeError("_new_index_meta only support visit only")
        assert self._anchor is not None
        if self._check_index_dumped(start_index):
            fname = visitor.encode_index_fname(
                    process_index, start_index, ExampleIdSuffix
                )
            fpath = os.path.join(self._example_dumped_dir(), fname)
            if not gfile.Exists(fpath):
                logging.fatal("%d has been dumpped however %s not "\
                              "in file system", start_index, fpath)
                os._exit(-1) # pylint: disable=protected-access
            return visitor.IndexMeta(process_index, start_index, fpath)
        return None

    def _sync_dumped_example_id_anchor(self):
        if self._anchor is None or self._visit_only:
            etcd_key = self._get_anchor_etcd_key()
            data = self._etcd.get_data(etcd_key)
            anchor = dj_pb.DumpedExampleIdAnchor()
            if data is None:
                self._anchor = \
                    dj_pb.DumpedExampleIdAnchor(undumped=empty_pb2.Empty())
            else:
                self._anchor = \
                    text_format.Parse(data, dj_pb.DumpedExampleIdAnchor())
        return self._anchor

    def _get_anchor_etcd_key(self):
        return '/'.join([self._data_source.data_source_meta.name,
                        'dumped_example_id_anchor',
                        'partition_{}'.format(self._partition_id)])

    def _example_dumped_dir(self):
        return os.path.join(self._data_source.example_dumped_dir,
                            'partition_{}'.format(self._partition_id))

    def _check_index_dumped(self, index):
        return self._anchor is not None and \
                self._anchor.HasField('last_meta') and \
                self._anchor.last_meta.end_index >= index

    def _make_directory_if_nessary(self):
        example_dumped_dir = self._example_dumped_dir()
        if not gfile.Exists(example_dumped_dir):
            gfile.MakeDirs(example_dumped_dir)
        if not gfile.IsDirectory(example_dumped_dir):
            logging.fatal("%s should be directory", example_dumped_dir)
            os._exit(-1) # pylint: disable=protected-access

class ExampleIdVisitor(visitor.Visitor):
    class ExampleIdItem(raw_data_iter.RawDataIter.Item):
        def __init__(self, record):
            self._record_str = record
            self._dumped_example_id = dj_pb.SyncedExampleId()
            self._dumped_example_id.ParseFromString(record)

        @property
        def example_id(self):
            return self._dumped_example_id.example_id

        @property
        def event_time(self):
            return self._dumped_example_id.event_time

        def __getattr__(self, attr):
            return getattr(self._dumped_example_id, attr)

    class ExampleIdIter(tf_record_iter.TfRecordIter):
        @classmethod
        def name(cls):
            return 'EXAMPLE_ID_TF_RECORD'

        def _inner_iter(self, fpath):
            with make_tf_record_iter(fpath) as record_iter:
                for record in record_iter:
                    yield ExampleIdVisitor.ExampleIdItem(record)

    def __init__(self, etcd, data_source, partition_id):
        super(ExampleIdVisitor, self).__init__(
                "example_id_visitor",
                ExampleIdManager(etcd, data_source, partition_id, True)
            )

    def active_visitor(self):
        end_index = self._index_mata_manager.get_last_dumped_index()
        if end_index is not None and \
                (self._end_index is None or self._end_index < end_index):
            self._set_end_index(end_index)
            self._finished = False

    def _new_iter(self):
        return ExampleIdVisitor.ExampleIdIter(None)

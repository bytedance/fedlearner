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
import traceback

from google.protobuf import text_format, empty_pb2

import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile
import tensorflow.compat.v1 as tf

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join import visitor
from fedlearner.data_join.common import (
    DoneFileSuffix, make_tf_record_iter,
    partition_repr, example_id_anchor_kvstore_key,
    data_source_example_dumped_dir,
    SYNC_ALLOWED_OPTIONAL_FIELDS,
    convert_tf_example_to_dict
)
from fedlearner.data_join.raw_data_iter_impl import (
    tf_record_iter, raw_data_iter
)

def encode_example_id_dumped_fname(process_index, start_index):
    return '{:06}-{:08}{}'.format(process_index, start_index, DoneFileSuffix)

def decode_index_meta(fpath):
    fname = os.path.basename(fpath)
    index_str = fname[:-len(DoneFileSuffix)]
    try:
        items = index_str.split('-')
        if len(items) != 2:
            raise RuntimeError("fname {} format error".format(fname))
        process_index, start_index = int(items[0]), int(items[1])
    except Exception as e: # pylint: disable=broad-except
        logging.fatal("fname %s not satisfied with pattern process_index-"\
                      "start_index", fname)
        traceback.print_stack()
        os._exit(-1) # pylint: disable=protected-access
    else:
        return visitor.IndexMeta(process_index, start_index, fpath)
    return None

class ExampleIdManager(visitor.IndexMetaManager):
    def __init__(self, kvstore, data_source, partition_id, visit_only):
        self._kvstore = kvstore
        self._data_source = data_source
        self._partition_id = partition_id
        self._visit_only = visit_only
        self._make_directory_if_nessary()
        index_metas = []
        if visit_only:
            index_metas = self._preload_example_id_meta()
        super(ExampleIdManager, self).__init__(index_metas)
        self._anchor = None
        self._sync_dumped_example_id_anchor()
        if self._visit_only:
            assert self._anchor is not None, \
                "the example id anchor must not None after sync anchor"
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
            if anchor.HasField('last_meta'):
                return anchor.last_meta.end_index
            return None

    def check_index_meta_by_process_index(self, process_index):
        with self._lock:
            self._sync_dumped_example_id_anchor()
            if self._anchor.HasField('undumped'):
                return False
            dumped_process_index = self._anchor.last_meta.process_index
            return dumped_process_index >= process_index

    def update_dumped_example_id_anchor(self, index_meta, end_index):
        process_index = index_meta.process_index
        start_index = index_meta.start_index
        fpath = index_meta.fpath
        dirname = os.path.dirname(fpath)
        fname = os.path.basename(fpath)
        if not gfile.Exists(fpath):
            raise ValueError("file {} is not existed".format(fpath))
        if dirname != self._example_dumped_dir():
            raise ValueError("file {} should be in {}".format(
                             fpath, self._example_dumped_dir()))
        if start_index > end_index:
            raise ValueError("bad index range[{}, {}]".format(
                              start_index, end_index))
        encode_fname = encode_example_id_dumped_fname(process_index,
                                                      start_index)
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
            kvstore_key = example_id_anchor_kvstore_key(
                    self._data_source.data_source_meta.name,
                    self._partition_id
                )
            self._kvstore.set_data(
                    kvstore_key, text_format.MessageToString(new_anchor)
                )
            self._anchor = new_anchor

    def get_example_dumped_dir(self):
        return self._example_dumped_dir()

    def _preload_example_id_meta(self):
        fdir = self._example_dumped_dir()
        fpaths = [os.path.join(fdir, f) for f in gfile.ListDirectory(fdir)
                  if f.endswith(DoneFileSuffix)]
        index_metas = []
        for fpath in fpaths:
            index_meta = decode_index_meta(fpath)
            assert index_meta is not None, "the index meta should not None "\
                                           "if decode index meta success"
            index_metas.append(index_meta)
        index_metas = sorted(index_metas, key=lambda meta: meta.start_index)
        for index, index_meta in enumerate(index_metas):
            if index != index_meta.process_index:
                logging.fatal("%s has error process index. expected %d",
                              index_meta.fpath, index)
                traceback.print_stack()
                os._exit(-1) # pylint: disable=protected-access
        return index_metas

    def _decode_index_meta(self, fpath):
        fname = os.path.basename(fpath)
        index_str = fname[:-len(DoneFileSuffix)]
        try:
            items = index_str.split('-')
            if len(items) != 2:
                raise RuntimeError("fname {} format error".format(fname))
            process_index, start_index = int(items[0]), int(items[1])
        except Exception as e: # pylint: disable=broad-except
            logging.fatal("fname %s not satisfied with pattern process_index-"\
                          "start_index", fname)
            traceback.print_stack()
            os._exit(-1) # pylint: disable=protected-access
        else:
            return visitor.IndexMeta(process_index, start_index, fpath)
        return None

    def _new_index_meta(self, process_index, start_index):
        if not self._visit_only:
            raise RuntimeError("_new_index_meta only support visit only")
        assert self._anchor is not None, "anchor is always in visit_only mode"
        if self._check_index_dumped(start_index):
            fname = encode_example_id_dumped_fname(process_index,
                                                   start_index)
            fpath = os.path.join(self._example_dumped_dir(), fname)
            if not gfile.Exists(fpath):
                logging.fatal("%d has been dumpped however %s not "\
                              "in file system", start_index, fpath)
                traceback.print_stack()
                os._exit(-1) # pylint: disable=protected-access
            return visitor.IndexMeta(process_index, start_index, fpath)
        return None

    def _sync_dumped_example_id_anchor(self):
        if self._anchor is None or self._visit_only:
            kvstore_key = example_id_anchor_kvstore_key(
                    self._data_source.data_source_meta.name,
                    self._partition_id
                )
            data = self._kvstore.get_data(kvstore_key)
            anchor = dj_pb.DumpedExampleIdAnchor()
            if data is None:
                self._anchor = \
                    dj_pb.DumpedExampleIdAnchor(undumped=empty_pb2.Empty())
            else:
                self._anchor = \
                    text_format.Parse(data, dj_pb.DumpedExampleIdAnchor(),
                                      allow_unknown_field=True)
        return self._anchor

    def _example_dumped_dir(self):
        return os.path.join(data_source_example_dumped_dir(self._data_source),
                            partition_repr(self._partition_id))

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
            traceback.print_stack()
            os._exit(-1) # pylint: disable=protected-access

class ExampleIdVisitor(visitor.Visitor):
    class ExampleIdItem(raw_data_iter.RawDataIter.Item):
        def __init__(self, index, row):
            super().__init__()
            row['index'] = index
            self._features.update(row)

    class ExampleIdIter(tf_record_iter.TfRecordIter):
        @classmethod
        def name(cls):
            return 'EXAMPLE_ID_TF_RECORD'

        def _inner_iter(self, fpath):
            with make_tf_record_iter(fpath) as record_iter:
                for record in record_iter:
                    lite_example_ids = dj_pb.LiteExampleIds()
                    lite_example_ids.ParseFromString(record)
                    tf_example = tf.train.Example(
                        features=lite_example_ids.features)
                    rows = convert_tf_example_to_dict(tf_example)

                    example_id_num = len(rows['example_id'])
                    index = 0
                    while index < example_id_num:
                        row = dict()
                        for fn in SYNC_ALLOWED_OPTIONAL_FIELDS:
                            if fn not in rows:
                                continue
                            value_list = rows[fn]
                            if len(value_list) > 0:
                                row[fn] = value_list[index]
                        example_id_item = ExampleIdVisitor.ExampleIdItem(
                                index + lite_example_ids.begin_index,
                                row
                            )
                        yield example_id_item
                        index += 1

    def __init__(self, kvstore, data_source, partition_id):
        super(ExampleIdVisitor, self).__init__(
                "example_id_visitor",
                ExampleIdManager(kvstore, data_source, partition_id, True)
            )

    def active_visitor(self):
        end_index = self._index_mata_manager.get_last_dumped_index()
        if end_index is not None and \
                (self._end_index is None or self._end_index < end_index):
            self._set_end_index(end_index)
            self._finished = False

    def _new_iter(self):
        return ExampleIdVisitor.ExampleIdIter(None)

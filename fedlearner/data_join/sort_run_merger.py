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

try:
    import queue
except ImportError:
    import Queue as queue
import logging
import threading
import os

import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile

from fedlearner.data_join.raw_data_iter_impl import create_raw_data_iter
from fedlearner.data_join import common, visitor
from fedlearner.data_join.output_writer_impl import create_output_writer

class MergedSortRunMeta(object):
    def __init__(self, partition_id, process_index):
        self._partition_id = partition_id
        self._process_index = process_index

    def encode_merged_sort_run_fname(self):
        return 'part-{:04}.{:08}{}'.format(self._partition_id,
                                           self._process_index,
                                           common.RawDataFileSuffix)

    @property
    def process_index(self):
        return self._process_index

    def __lt__(self, other):
        assert isinstance(other, MergedSortRunMeta)
        assert other._partition_id == other._partition_id
        return self._process_index < other._process_index

    @classmethod
    def decode_sort_run_meta_from_fname(cls, fname):
        if not fname.endswith(common.RawDataFileSuffix):
            raise RuntimeError("fname of MergedSortRun should endswith "\
                               "{}".format(common.RawDataFileSuffix))
        if not fname.startswith('part-'):
            raise RuntimeError("fname of MergedSortRun should startswith "\
                               "{}".format('part-'))
        segs = fname[len('part-'):-len(common.RawDataFileSuffix)].split('.')
        if len(segs) != 2:
            raise RuntimeError("fname: {} should format as "\
                               "part-partition_id-process_index{}"\
                               .format(fname, common.RawDataFileSuffix))
        return MergedSortRunMeta(int(segs[0]), int(segs[1]))

class SortRunReader(object):
    class MergeItem(object):
        def __init__(self, item, reader_index, comparator):
            self._item = item
            self._reader_index = reader_index
            self._comparator = comparator

        @property
        def inner_item(self):
            return self._item

        @property
        def reader_index(self):
            return self._reader_index

        def __lt__(self, other):
            assert isinstance(other, SortRunReader.MergeItem)
            return self._comparator(self._item, other._item)

        def __getattr__(self, attr):
            return getattr(self._item, attr)

    def __init__(self, reader_index, fpath,
                 reader_options, comparator):
        self._reader_index = reader_index
        self._fpath = fpath
        self._reader_options = reader_options
        self._comparator = comparator
        self._fiter = None
        if gfile.Exists(fpath):
            self._finished = False
        else:
            self._finished = True

    def finished(self):
        return self._finished

    def __iter__(self):
        return self

    def __next__(self):
        return self._next_internal()

    def next(self):
        return self._next_internal()

    def _next_internal(self):
        if not self._finished:
            try:
                item = None
                if self._fiter is None:
                    self._fiter = create_raw_data_iter(self._reader_options)
                    meta = visitor.IndexMeta(0, 0, self._fpath)
                    self._fiter.reset_iter(meta, True)
                    item = self._fiter.get_item()
                else:
                    _, item = next(self._fiter)
                assert item is not None
                return SortRunReader.MergeItem(item, self._reader_index,
                                               self._comparator)
            except StopIteration:
                self._finished = True
        raise StopIteration("%s has been iter finished" % self._fpath)

class SortRunMergerWriter(object):
    def __init__(self, base_dir, process_index, partition_id, writer_options):
        self._merged_dir = \
            os.path.join(base_dir, common.partition_repr(partition_id))
        self._partition_id = partition_id
        self._writer_options = writer_options
        self._process_index = process_index
        self._writer = None
        self._merged_fpaths = []
        self._merged_num = 0
        self._tmp_fpath = None

    def append(self, item):
        self._get_output_writer().write_item(item)
        self._merged_num += 1
        if self._merged_num % (1 << 20) == 0:
            self._finish_writer()

    def finish(self):
        self._finish_writer()
        logging.warning("merge %d record in %d sort run merger: "\
                        "for partition %d", self._merged_num,
                        self._process_index, self._partition_id)
        finish_tag_fpath = os.path.join(self._merged_dir, '_SUCCESS')
        with gfile.GFile(finish_tag_fpath, 'w') as fh:
            fh.write('\n')
        return self._merged_fpaths

    def _finish_writer(self):
        if self._writer is not None:
            self._writer.close()
            meta = MergedSortRunMeta(self._partition_id,
                                     self._process_index)
            fname = meta.encode_merged_sort_run_fname()
            fpath = os.path.join(self._merged_dir, fname)
            gfile.Rename(self._tmp_fpath, fpath, True)
            self._merged_fpaths.append(fpath)
            self._writer = None
            self._process_index += 1

    def _get_output_writer(self):
        if self._writer is None:
            self._tmp_fpath = common.gen_tmp_fpath(self._merged_dir)
            self._writer = create_output_writer(self._writer_options,
                                                self._tmp_fpath)
        return self._writer

class SortRunMerger(object):
    def __init__(self, options, comparator):
        self._lock = threading.Lock()
        self._options = options
        self._merge_finished = False
        self._comparator = comparator
        self._merged_dir = os.path.join(
                self._options.output_file_dir,
                common.partition_repr(self._partition_id)
            )
        self._create_merged_dir_if_need()

    def merge_sort_runs(self, input_fpaths):
        if self._check_merged():
            logging.info("sort runs have been merged for partition %d",
                         self._partition_id)
            return self._list_merged_sort_run_fpath()
        if len(input_fpaths) == 0:
            logging.info("no sort run for partition %d", self._partition_id)
            return []
        dumped_item, next_process_index = self._sync_merged_state()
        readers = self._create_sort_run_readers(input_fpaths)
        pque = queue.PriorityQueue(len(input_fpaths) + 1)
        for idx, reader in enumerate(readers):
            if not reader.finished():
                for item in reader:
                    if dumped_item is None or \
                            not self._comparator(item, dumped_item):
                        pque.put(item)
                        break
        writer = self._create_sort_run_merger_writer(next_process_index)
        while pque.qsize() > 0:
            item = pque.get()
            writer.append(item.inner_item)
            assert item.reader_index < len(readers)
            self._replenish_item(readers[item.reader_index], pque)
        writer.finish()
        return self._list_merged_sort_run_fpath()

    def is_merged_finished(self):
        with self._lock:
            return self._merge_finished

    def set_merged_finished(self):
        with self._lock:
            self._merge_finished = True

    @classmethod
    def _replenish_item(cls, reader, pque):
        if not reader.finished():
            for item in reader:
                pque.put(item)
                break

    def _create_sort_run_readers(self, input_fpaths):
        assert len(input_fpaths) > 0
        readers = []
        for index, input_fpath in enumerate(input_fpaths):
            reader = SortRunReader(index, input_fpath,
                                   self._options.reader_options,
                                   self._comparator)
            readers.append(reader)
        return readers

    def _create_sort_run_merger_writer(self, process_index):
        return SortRunMergerWriter(self._options.output_file_dir,
                                   process_index, self._partition_id,
                                   self._options.writer_options)

    def _check_merged(self):
        return gfile.Exists(os.path.join(self._merged_dir, '_SUCCESS'))

    def _list_merged_sort_run_fpath(self):
        metas = [MergedSortRunMeta.decode_sort_run_meta_from_fname(f)

                 for f in gfile.ListDirectory(self._merged_dir) if
                 f.endswith(common.RawDataFileSuffix)]
        metas.sort()
        return [os.path.join(self._merged_dir,
                             meta.encode_merged_sort_run_fname())
                for meta in metas]

    def _create_merged_dir_if_need(self):
        if not gfile.Exists(self._merged_dir):
            gfile.MakeDirs(self._merged_dir)
        assert gfile.IsDirectory(self._merged_dir)

    def _sync_merged_state(self):
        self._create_merged_dir_if_need()
        fnames = gfile.ListDirectory(self._merged_dir)
        metas = []
        for fname in fnames:
            if fname.endswith(common.TmpFileSuffix):
                gfile.Remove(os.path.join(self._merged_dir, fname))
            if fname.endswith(common.RawDataFileSuffix):
                meta = MergedSortRunMeta.decode_sort_run_meta_from_fname(fname)
                metas.append(meta)
        metas.sort()
        if len(metas) == 0:
            return None, 0
        last_meta = metas[-1]
        fpath = os.path.join(self._merged_dir,
                             last_meta.encode_merged_sort_run_fname())
        last_item = None
        for item in SortRunReader(0, fpath, self._options.reader_options,
                                  self._comparator):
            last_item = item
        assert last_item is not None
        return last_item, last_meta.process_index + 1

    @property
    def _partition_id(self):
        return self._options.partition_id

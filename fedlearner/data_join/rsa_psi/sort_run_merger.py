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

from tensorflow.compat.v1 import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join import common, visitor, csv_dict_writer
from fedlearner.data_join.raw_data_iter_impl.csv_dict_iter import CsvDictIter

class MergedSortRunMeta(object):
    def __init__(self, partition_id, process_index):
        self._partition_id = partition_id
        self._process_index = process_index

    def encode_merged_sort_run_fname(self):
        return 'part-{:04}-{:08}{}'.format(self._partition_id,
                                           self._process_index,
                                           common.MergedSortRunSuffix)

    @property
    def process_index(self):
        return self._process_index

    def __lt__(self, other):
        assert isinstance(other, MergedSortRunMeta)
        assert other._partition_id == other._partition_id
        return self._process_index < other._process_index

    @classmethod
    def decode_sort_run_meta_from_fname(cls, fname):
        if not fname.endswith(common.MergedSortRunSuffix):
            raise RuntimeError("fname of MergedSortRun should endswith "\
                               "{}".format(common.MergedSortRunSuffix))
        if not fname.startswith('part-'):
            raise RuntimeError("fname of MergedSortRun should startswith "\
                               "{}".format('part-'))
        segs = fname[len('part-'):-len(common.MergedSortRunSuffix)].split('-')
        if len(segs) != 2:
            raise RuntimeError("fname: {} should format as "\
                               "part-partition_id-process_index{}"\
                               .format(fname, common.MergedSortRunSuffix))
        return MergedSortRunMeta(int(segs[0]), int(segs[1]))

class SortRunReader(object):
    class MergeItem(object):
        def __init__(self, raw, reader_index):
            self._raw = raw
            self._reader_index = reader_index

        @property
        def join_id(self):
            return self._raw.example_id

        @property
        def reader_index(self):
            return self._reader_index

        @property
        def raw(self):
            return self._raw.record

        def __lt__(self, other):
            assert isinstance(other, SortRunReader.MergeItem)
            return self.join_id < other.join_id

    def __init__(self, reader_index, fpath, read_ahead_size):
        self._reader_index = reader_index
        self._fpath = fpath
        self._read_ahead_size = read_ahead_size
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
                    raw_data_options = dj_pb.RawDataOptions(
                            raw_data_iter='CSV_DICT',
                            read_ahead_size=self._read_ahead_size
                        )
                    self._fiter = CsvDictIter(raw_data_options)
                    meta = visitor.IndexMeta(0, 0, self._fpath)
                    self._fiter.reset_iter(meta, True)
                    item = self._fiter.get_item()
                else:
                    _, item = next(self._fiter)
                assert item is not None
                return SortRunReader.MergeItem(item, self._reader_index)
            except StopIteration:
                self._finished = True
        raise StopIteration("%s has been iter finished" % self._fpath)

class SortRunMergerWriter(object):
    def __init__(self, base_dir, process_index, partition_id):
        self._merged_dir = \
            os.path.join(base_dir, common.partition_repr(partition_id))
        self._partition_id = partition_id
        self._process_index = process_index
        self._csv_dict_writer = None
        self._merged_fpaths = []
        self._merged_num = 0
        self._tmp_fpath = None

    def append(self, raw):
        writer = self._get_csv_dict_writer()
        writer.write(raw)
        self._merged_num += 1
        if writer.write_raw_num() > (1 << 18):
            self._finish_csv_dict_writer()

    def finish(self):
        self._finish_csv_dict_writer()
        logging.warning("merge %d record in %d sort run merger: "\
                        "for partition %d", self._merged_num,
                        self._process_index, self._partition_id)
        finish_tag_fpath = os.path.join(self._merged_dir, '_SUCCESS')
        with gfile.GFile(finish_tag_fpath, 'w') as fh:
            fh.write('\n')
        return self._merged_fpaths

    def get_merged_fpaths(self):
        return self._merged_fpaths

    def _finish_csv_dict_writer(self):
        if self._csv_dict_writer is not None:
            self._csv_dict_writer.close()
            if self._csv_dict_writer.write_raw_num() == 0:
                gfile.Remove(self._tmp_fpath)
            else:
                meta = MergedSortRunMeta(self._partition_id,
                                         self._process_index)
                fname = meta.encode_merged_sort_run_fname()
                fpath = os.path.join(self._merged_dir, fname)
                gfile.Rename(self._tmp_fpath, fpath, True)
                self._merged_fpaths.append(fpath)
                self._csv_dict_writer = None
                self._process_index += 1

    def _get_csv_dict_writer(self):
        if self._csv_dict_writer is None:
            self._tmp_fpath = common.gen_tmp_fpath(self._merged_dir)
            self._csv_dict_writer = \
                    csv_dict_writer.CsvDictWriter(self._tmp_fpath)
        return self._csv_dict_writer

class SortRunMerger(object):
    def __init__(self, input_dir, options):
        self._lock = threading.Lock()
        self._input_dir = input_dir
        self._options = options
        self._merge_finished = False
        self._merged_dir = os.path.join(
                self._options.output_file_dir,
                common.partition_repr(self._partition_id)
            )
        self._create_merged_dir_if_need()

    def merge_sort_runs(self, sort_runs):
        if self._check_merged():
            logging.info("sort runs have been merged for partition %d",
                         self._partition_id)
            return self._list_merged_sort_run_fpath()
        if len(sort_runs) == 0:
            logging.info("no sort run for partition %d", self._partition_id)
            return []
        dumped_key, next_process_index = self._sync_merged_state()
        readers = self._create_sort_run_readers(sort_runs)
        pque = queue.PriorityQueue(len(sort_runs)*2+1)
        for idx, reader in enumerate(readers):
            if not reader.finished():
                for item in reader:
                    if dumped_key is None or item.join_id >= dumped_key:
                        pque.put(item)
                        break
        writer = self._create_sort_run_merger_writer(next_process_index)
        while pque.qsize() > 0:
            item = pque.get()
            writer.append(item.raw)
            assert item.reader_index < len(readers)
            self._replenish_item(readers[item.reader_index], pque)
        writer.finish()
        return writer.get_merged_fpaths()

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

    def _create_sort_run_readers(self, sort_runs):
        assert len(sort_runs) > 0
        readers = []
        for index, sort_run in enumerate(sort_runs):
            fpath = os.path.join(self._input_dir,
                                 common.partition_repr(self._partition_id),
                                 sort_run.encode_sort_run_fname())
            reader = SortRunReader(
                    index, fpath,
                    self._options.sort_run_merger_read_ahead_buffer
                )
            readers.append(reader)
        return readers

    def _create_sort_run_merger_writer(self, process_index):
        return SortRunMergerWriter(self._options.output_file_dir,
                                   process_index, self._partition_id)

    def _check_merged(self):
        return gfile.Exists(os.path.join(self._merged_dir, '_SUCCESS'))

    def _list_merged_sort_run_fpath(self):
        metas = [MergedSortRunMeta.decode_sort_run_meta_from_fname(f)

                 for f in gfile.ListDirectory(self._merged_dir) if
                 f.endswith(common.MergedSortRunSuffix)]
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
        found_tmp = False
        fnames = gfile.ListDirectory(self._merged_dir)
        metas = []
        for fname in fnames:
            if fname.endswith(common.TmpFileSuffix):
                found_tmp = True
            if fname.endswith(common.MergedSortRunSuffix):
                meta = MergedSortRunMeta.decode_sort_run_meta_from_fname(fname)
                metas.append(meta)
        metas.sort()
        if not found_tmp:
            metas = metas[:-1]
        if len(metas) == 0:
            return None, 0
        last_meta = metas[-1]
        fpath = os.path.join(self._merged_dir,
                             last_meta.encode_merged_sort_run_fname())
        last_item = None
        for item in SortRunReader(0, fpath, 1 << 20):
            last_item = item
        assert last_item is not None
        return last_item.join_id, last_meta.process_index + 1

    @property
    def _partition_id(self):
        return self._options.partition_id

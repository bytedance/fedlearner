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
import re
import copy
from os import path

import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile

from fedlearner.data_join.output_writer_impl import create_output_writer
from fedlearner.data_join.common import (DoneFileSuffix, TmpFileSuffix,
                                         gen_tmp_fpath, partition_repr)

class SortRunMeta(object):
    def __init__(self, process_index, start_index, end_index):
        self._process_index = process_index
        self._start_index = start_index
        self._end_index = end_index

    @property
    def process_index(self):
        return self._process_index

    @property
    def start_index(self):
        return self._start_index

    @property
    def end_index(self):
        return self._end_index

    def __lt__(self, other):
        assert isinstance(other, SortRunMeta)
        return self._process_index < other._process_index

    @classmethod
    def decode_sort_run_meta_from_fname(cls, fname):
        if not fname.endswith(DoneFileSuffix):
            raise RuntimeError(
                    "fname of SortRun should endwith {}".format(DoneFileSuffix)
                )
        segs = re.split('\.|-', fname[:-len(DoneFileSuffix)]) # pylint: disable=anomalous-backslash-in-string
        if len(segs) != 3:
            raise RuntimeError("fname: {} should format as "\
                               "process_index.start_index-end_index.{}"\
                               .format(fname, DoneFileSuffix))
        return SortRunMeta(int(segs[0]), int(segs[1]), int(segs[2]))

    def encode_sort_run_fname(self):
        return '{:05}.{:08}-{:08}{}'.format(
                self._process_index, self._start_index,
                self._end_index, DoneFileSuffix
            )

class SortRunDumper(object):
    class SortRunWriter(object):
        def __init__(self, process_index, output_dir, writer_options):
            self._process_index = process_index
            self._output_dir = output_dir
            self._tmp_fpath = self._gen_tmp_fpath()
            self._writer_options = writer_options
            self._fpath = None
            self._writer = None
            self._start_index = None
            self._end_index = None

        def append(self, index, item):
            self._get_output_writer(self._tmp_fpath).write_item(item)
            if self._start_index is None or self._start_index > index:
                self._start_index = index
            if self._end_index is None or self._end_index < index:
                self._end_index = index

        def finish_dumper(self):
            self._writer.close()
            meta = None
            if self._start_index is None or self._end_index is None:
                gfile.Remove(self._fpath)
            else:
                meta = SortRunMeta(self._process_index,
                                   self._start_index,
                                   self._end_index)
                fname = meta.encode_sort_run_fname()
                self._fpath = path.join(self._output_dir, fname)
                gfile.Rename(self._tmp_fpath, self._fpath, True)
            return meta

        @property
        def tmp_fpath(self):
            return self._tmp_fpath

        @property
        def fpath(self):
            return self._fpath

        def _get_output_writer(self, fpath):
            if self._writer is None:
                self._writer = create_output_writer(
                        self._writer_options, fpath
                    )
            return self._writer

        def _gen_tmp_fpath(self):
            return gen_tmp_fpath(self._output_dir)

    def __init__(self, options):
        self._lock = threading.Lock()
        self._dumped_process_index = None
        self._next_index_to_dump = None
        self._options = options
        self._dump_finished = False
        self._dumped_sort_run_metas = []
        self._fly_sort_run_dumper = None
        self._sync_manager_state(True)

    def get_next_index_to_dump(self):
        with self._lock:
            return self._next_index_to_dump

    def finish_dump_sort_run(self):
        succ_tag_fpath = self._get_finish_tag_fpath()
        with gfile.GFile(succ_tag_fpath, 'w') as fh:
            fh.write('finished')
        with self._lock:
            self._dump_finished = True

    def is_dump_finished(self):
        with self._lock:
            return self._dump_finished

    def dump_sort_runs(self, producer):
        self._sync_manager_state(False)
        if self.is_dump_finished():
            return
        assert self._dumped_process_index is not None
        assert self._fly_sort_run_dumper is None
        next_process_index = self._dumped_process_index + 1
        self._fly_sort_run_dumper = self._create_sort_run_dumper(
                next_process_index
            )
        for join_id, index, item in producer:
            self._fly_sort_run_dumper.append(index, item)
        meta = self._fly_sort_run_dumper.finish_dumper()
        if meta is not None:
            self._dumped_sort_run_metas.append(meta)
            with self._lock:
                assert self._next_index_to_dump <= meta.end_index
                self._next_index_to_dump = meta.end_index + 1
        self._dumped_process_index += 1

    def get_all_sort_runs(self):
        if not self._double_check_dump_finished():
            raise RuntimeError("sort runs have not been dumped finished")
        with self._lock:
            return copy.deepcopy(self._dumped_sort_run_metas)

    def sort_run_dump_dir(self):
        return path.join(self._options.output_file_dir, 'sort_run_dump-tmp')

    def _sync_manager_state(self, init):
        if self._double_check_dump_finished() and not init:
            return
        if self._fly_sort_run_dumper is not None:
            if gfile.Exists(self._fly_sort_run_dumper.tmp_fpath):
                gfile.Remove(self._fly_sort_run_dumper.tmp_fpath)
            fpath = self._fly_sort_run_dumper.fpath
            if fpath is not None and gfile.Exists(fpath):
                fname = path.basename(fpath)
                meta = SortRunMeta.decode_sort_run_meta_from_fname(fname)
                self._dumped_sort_run_metas.append(meta)
                self._dumped_process_index = meta.process_index
        self._fly_sort_run_dumper = None
        if self._dumped_process_index is None:
            self._dumped_sort_run_metas = \
                    [SortRunMeta.decode_sort_run_meta_from_fname(fname)
                     for fname in self._list_dumper_output_dir()]
            self._dumped_sort_run_metas.sort()
            if len(self._dumped_sort_run_metas) == 0:
                self._dumped_process_index = -1
            else:
                self._dumped_process_index = \
                        self._dumped_sort_run_metas[-1].process_index
        with self._lock:
            self._next_index_to_dump = \
                    0 if len(self._dumped_sort_run_metas) == 0 \
                    else self._dumped_sort_run_metas[-1].end_index + 1

    def _list_dumper_output_dir(self):
        output_dir = self._get_output_dir()
        if gfile.Exists(output_dir):
            assert gfile.IsDirectory(output_dir)
            all_files = gfile.ListDirectory(output_dir)
            for f in all_files:
                if f.endswith(TmpFileSuffix):
                    gfile.Remove(path.join(output_dir, f))
            return [f for f in all_files if f.endswith(DoneFileSuffix)]
        gfile.MakeDirs(output_dir)
        return []

    def _create_sort_run_dumper(self, process_index):
        output_dir = self._get_output_dir()
        return SortRunDumper.SortRunWriter(process_index,
                                           output_dir,
                                           self._options.writer_options)

    def _get_output_dir(self):
        return path.join(self.sort_run_dump_dir(),
                         partition_repr(self._options.partition_id))

    def _get_finish_tag_fpath(self):
        return path.join(self._get_output_dir(), '_SUCCESS')

    def _set_dump_sort_run_finished(self):
        with self._lock:
            self._dump_finished = True

    def _double_check_dump_finished(self):
        if self.is_dump_finished():
            return True
        if gfile.Exists(self._get_finish_tag_fpath()):
            self._set_dump_sort_run_finished()
        return self.is_dump_finished()

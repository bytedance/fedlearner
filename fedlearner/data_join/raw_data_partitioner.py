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
import re
import gc
import traceback

import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile

from cityhash import CityHash32 # pylint: disable=no-name-in-module

from fedlearner.common.db_client import DBClient

from fedlearner.data_join.output_writer_impl import create_output_writer
from fedlearner.data_join.item_batch_seq_processor import \
        ItemBatch, ItemBatchSeqProcessor
from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.raw_data_iter_impl.metric_stats import MetricStats
from fedlearner.data_join.raw_data_visitor import FileBasedMockRawDataVisitor
from fedlearner.data_join import common

class RawDataBatch(ItemBatch):
    def __init__(self, begin_index):
        self._begin_index = begin_index
        self._raw_datas = []

    @property
    def begin_index(self):
        return self._begin_index

    def __len__(self):
        return len(self._raw_datas)

    def __lt__(self, other):
        assert isinstance(other, RawDataBatch)
        return self.begin_index < other.begin_index

    def __iter__(self):
        return iter(self._raw_datas)

    def append(self, item):
        self._raw_datas.append(item)

class RawDataBatchFetcher(ItemBatchSeqProcessor):
    def __init__(self, kvstore, options):
        super(RawDataBatchFetcher, self).__init__(
                options.batch_processor_options.max_flying_item,
            )
        self._raw_data_visitor = FileBasedMockRawDataVisitor(
                kvstore, options.raw_data_options,
                '{}-partitioner-mock-data-source-{:04}'.format(
                        options.partitioner_name,
                        options.partitioner_rank_id
                    ),
                options.input_file_paths
            )
        self._batch_size = options.batch_processor_options.batch_size
        self._metrics_tags = {
            'partition_name': options.partitioner_name,
            'partition': options.partitioner_rank_id
        }
        self._metric_stats = MetricStats(options.raw_data_options,
                                         self._metrics_tags)
        self.set_input_finished()

    @classmethod
    def name(cls):
        return 'RawDataBatchFetcher'

    def _make_item_batch(self, begin_index):
        return RawDataBatch(begin_index)

    def _make_inner_generator(self, next_index):
        assert next_index is not None
        if next_index == 0:
            self._raw_data_visitor.reset()
        else:
            self._raw_data_visitor.seek(next_index - 1)
        while not self._raw_data_visitor.finished() and \
                not self._fly_item_full():
            next_batch = self._make_item_batch(next_index)
            for (index, item) in self._raw_data_visitor:
                if index != next_index:
                    logging.fatal("batch raw data visitor is not consecutive, "\
                                  "%d != %d", index, next_index)
                    traceback.print_stack()
                    os._exit(-1) # pylint: disable=protected-access
                self._metric_stats.emit_metric(item)
                next_batch.append(item)
                next_index += 1
                if len(next_batch) >= self._batch_size:
                    break
            yield next_batch, self._raw_data_visitor.finished()
        yield self._make_item_batch(next_index), \
                self._raw_data_visitor.finished()

    def cleanup_visitor_meta_data(self):
        self._raw_data_visitor.cleanup_meta_data()

class RawDataPartitioner(object):
    class FileMeta(object):
        def __init__(self, rank_id, process_index, begin_index, end_index):
            self._rank_id = rank_id
            self._process_index = process_index
            self._begin_index = begin_index
            self._end_index = end_index

        @property
        def process_index(self):
            return self._process_index

        @property
        def rank_id(self):
            return self._rank_id

        @property
        def begin_index(self):
            return self._begin_index

        @property
        def end_index(self):
            return self._end_index

        def __lt__(self, other):
            assert isinstance(other, RawDataPartitioner.FileMeta)
            assert self.rank_id == other.rank_id
            return self.process_index < other.process_index

        def encode_meta_to_fname(self):
            return '{:04}.{:08}.{:010}-{:010}{}'.format(
                    self.rank_id, self.process_index, self.begin_index,
                    self.end_index, common.RawDataFileSuffix
                )

        @classmethod
        def decode_meta_from_fname(cls, fname):
            assert fname.endswith(common.RawDataFileSuffix)
            segs = re.split('\.|-', fname[:-len(common.RawDataFileSuffix)]) # pylint: disable=anomalous-backslash-in-string
            assert len(segs) == 4
            return RawDataPartitioner.FileMeta(int(segs[0]), int(segs[1]),
                                               int(segs[2]), int(segs[3]))

    class OutputFileWriter(object):
        def __init__(self, options, partition_id, process_index):
            self._options = options
            self._partition_id = partition_id
            self._process_index = process_index
            self._begin_index = None
            self._end_index = None
            self._writer = None
            self._tmp_fpath = common.gen_tmp_fpath(
                    os.path.join(self._options.output_dir,
                                 common.partition_repr(self._partition_id))
                )

        def append_item(self, index, item):
            self._get_output_writer().write_item(item)
            if self._begin_index is None:
                self._begin_index = index
            self._end_index = index

        def finish(self):
            meta = None
            if self._writer is not None:
                self._writer.close()
                self._writer = None
                meta = RawDataPartitioner.FileMeta(
                        self._options.partitioner_rank_id,
                        self._process_index,
                        self._begin_index,
                        self._end_index
                    )
                fpath = os.path.join(self._options.output_dir,
                                     common.partition_repr(self._partition_id),
                                     meta.encode_meta_to_fname())
                gfile.Rename(self.get_tmp_fpath(), fpath, True)
            return meta

        def get_tmp_fpath(self):
            return self._tmp_fpath

        def destroy(self):
            if self._writer is not None:
                self._writer.close()
                self._writer = None
            if gfile.Exists(self._tmp_fpath):
                gfile.Remove(self._tmp_fpath)

        def __del__(self):
            self.destroy()

        def _get_output_writer(self):
            if self._writer is None:
                self._writer = create_output_writer(
                        self._options.writer_options,
                        self._tmp_fpath
                    )
            return self._writer

    def __init__(self, options, part_field,
                 kvstore_type, use_mock_etcd=False):
        self._options = options
        self._part_field = part_field
        kvstore = DBClient(kvstore_type, use_mock_etcd)
        self._raw_data_batch_fetcher = RawDataBatchFetcher(kvstore, options)
        self._next_part_index = None
        self._dumped_process_index = None
        self._flying_writers = []
        self._dumped_file_metas = {}
        self._worker_map = {}
        self._started = False
        self._part_finished = False
        self._cond = threading.Condition()

    def start_process(self):
        with self._cond:
            if not self._started:
                self._worker_map = {
                    'raw_data_batch_fetcher': RoutineWorker(
                    'raw_data_batch_fetcher',
                    self._raw_data_batch_fetch_fn,
                    self._raw_data_batch_fetch_cond, 5),

                    'raw_data_partitioner': RoutineWorker(
                    'raw_data_partitioner',
                    self._raw_data_part_fn,
                    self._raw_data_part_cond, 5)
                }
                for _, w in self._worker_map.items():
                    w.start_routine()
                self._started = True

    def stop_process(self):
        wait_join = True
        with self._cond:
            if self._started:
                wait_join = True
                self._started = False
        if wait_join:
            for w in self._worker_map.values():
                w.stop_routine()

    def wait_for_finished(self):
        while not self._is_part_finished():
            with self._cond:
                self._cond.wait()
        self.stop_process()
        self._raw_data_batch_fetcher.cleanup_visitor_meta_data()

    def _raw_data_part_fn(self):
        if self._check_finished_tag():
            logging.warning("raw data has been parttedfor rank id of parti"\
                            "tioner %d", self._options.partitioner_rank_id)
            self._notify_part_finished()
            return
        self._sync_partitioner_state()
        assert self._dumped_process_index is not None
        assert len(self._flying_writers) == 0
        fetcher = self._raw_data_batch_fetcher
        fetch_finished = False
        next_index = self._get_next_part_index()
        hint_index = None
        bp_options = self._options.batch_processor_options
        round_dumped_item = 0
        while not fetch_finished:
            fetch_finished, batch, hint_index = \
                    fetcher.fetch_item_batch_by_index(next_index, hint_index)
            if batch is not None:
                for index, item in enumerate(batch):
                    raw_id = getattr(item, self._part_field)
                    partition_id = CityHash32(raw_id) % \
                            self._options.output_partition_num
                    writer = self._get_file_writer(partition_id)
                    writer.append_item(batch.begin_index+index, item)
                next_index += len(batch)
                round_dumped_item += len(batch)
                fly_item_cnt = fetcher.get_flying_item_count()
                if round_dumped_item // self._options.output_partition_num \
                        > (1<<21) or \
                        common.get_heap_mem_stats(None).CheckOomRisk(
                            fly_item_cnt,
                            self._options.memory_limit_ratio-0.05):
                    self._finish_file_writers()
                    self._set_next_part_index(next_index)
                    hint_index = self._evict_staless_batch(hint_index,
                                                           next_index-1)
                    logging.info("consumed %d items", next_index-1)
                    gc_cnt = gc.collect()
                    logging.warning("finish writer partition trigger "\
                                    "gc %d actively", gc_cnt)
                    round_dumped_item = 0
                    self._wakeup_raw_data_fetcher()
            elif not fetch_finished:
                with self._cond:
                    self._cond.wait(1)
        self._finish_file_writers()
        self._dump_finished_tag()
        for partition_id, metas in self._dumped_file_metas.items():
            logging.info("part %d output %d files by partitioner",
                          partition_id, len(metas))
            for meta in metas:
                logging.info("%s", meta.encode_meta_to_fname())
            logging.info("-----------------------------------")
        self._notify_part_finished()

    def _raw_data_part_cond(self):
        if self._is_part_finished():
            self._notify_part_finished()
            return False
        return True

    def _notify_part_finished(self):
        with self._cond:
            self._part_finished = True
            self._cond.notify_all()

    def _is_part_finished(self):
        with self._cond:
            return self._part_finished

    def _get_file_writer(self, partition_id):
        if len(self._flying_writers) == 0:
            self._flying_writers = \
                    [RawDataPartitioner.OutputFileWriter(
                            self._options, pid,
                            self._dumped_process_index+1
                        )
                     for pid in range(self._options.output_partition_num)]
        assert partition_id < len(self._flying_writers)
        return self._flying_writers[partition_id]

    def _finish_file_writers(self):
        for partition_id, writer in enumerate(self._flying_writers):
            meta = writer.finish()
            if meta is not None:
                self._dumped_file_metas[partition_id].append(meta)
                logging.info("dump %s for partition %d",
                             meta.encode_meta_to_fname(), partition_id)
        self._flying_writers = []
        self._dumped_process_index += 1

    def _evict_staless_batch(self, hint_index, staless_index):
        evict_cnt = self._raw_data_batch_fetcher.evict_staless_item_batch(
                staless_index
            )
        if hint_index is not None:
            if hint_index <= evict_cnt:
                return 0
            return hint_index-evict_cnt
        return None

    def _set_next_part_index(self, next_part_index):
        with self._cond:
            self._next_part_index = next_part_index

    def _get_next_part_index(self):
        with self._cond:
            return self._next_part_index

    def _sync_partitioner_state(self):
        for writer in self._flying_writers:
            writer.destroy()
        self._flying_writers = []
        if self._dumped_process_index is None:
            max_process_index = None
            min_process_index = None
            for partition_id in range(self._options.output_partition_num):
                metas = self._list_file_metas(partition_id)
                metas.sort()
                self._dumped_file_metas[partition_id] = metas
                end_meta = None if len(metas) == 0 else metas[-1]
                if end_meta is None:
                    continue
                if min_process_index is None or \
                        min_process_index > end_meta.process_index:
                    min_process_index = end_meta.process_index
                if max_process_index is None or \
                        max_process_index < end_meta.process_index:
                    max_process_index = end_meta.process_index
            if max_process_index is None or min_process_index is None:
                self._dumped_process_index = -1
            elif max_process_index == min_process_index:
                self._dumped_process_index = max_process_index
            else:
                self._dumped_process_index = max_process_index - 1
        max_dumped_index = -1
        for partition_id, metas in self._dumped_file_metas.items():
            for meta in metas[::-1]:
                if meta.process_index > self._dumped_process_index:
                    fpath = os.path.join(self._options.output_dir,
                                         common.partition_repr(partition_id),
                                         meta.encode_meta_to_fname())
                    if gfile.Exists(fpath):
                        gfile.Remove(fpath)
                else:
                    break
            metas = metas[:self._dumped_process_index+1]
            self._dumped_file_metas[partition_id] = metas
            if len(metas) > 0 and metas[-1].end_index > max_dumped_index:
                max_dumped_index = metas[-1].end_index
        self._set_next_part_index(max_dumped_index+1)

    def _list_file_metas(self, partition_id):
        dumped_dir = os.path.join(self._options.output_dir,
                                  common.partition_repr(partition_id))
        if not gfile.Exists(dumped_dir):
            gfile.MakeDirs(dumped_dir)
        assert gfile.IsDirectory(dumped_dir)
        fnames = [os.path.basename(f) for f in gfile.ListDirectory(dumped_dir)
                  if f.endswith(common.RawDataFileSuffix)]
        metas = [RawDataPartitioner.FileMeta.decode_meta_from_fname(f)
                 for f in fnames]
        return [meta for meta in metas \
                if meta.rank_id == self._options.partitioner_rank_id]

    def _raw_data_batch_fetch_fn(self):
        next_part_index = self._get_next_part_index()
        fetcher = self._raw_data_batch_fetcher
        for batch in fetcher.make_processor(next_part_index):
            logging.debug("fetch batch begin at %d, len %d. wakeup "\
                          "partitioner", batch.begin_index, len(batch))
            self._wakeup_partitioner()
            fly_item_cnt = fetcher.get_flying_item_count()
            if common.get_heap_mem_stats(None).CheckOomRisk(
                fly_item_cnt, self._options.memory_limit_ratio):
                logging.warning('early stop the raw data fetch '\
                                'since the oom risk')
                break

    def _raw_data_batch_fetch_cond(self):
        next_part_index = self._get_next_part_index()
        fetcher = self._raw_data_batch_fetcher
        fly_item_cnt = fetcher.get_flying_item_count()
        return self._raw_data_batch_fetcher.need_process(next_part_index) and \
                not common.get_heap_mem_stats(None).CheckOomRisk(
                    fly_item_cnt, self._options.memory_limit_ratio)

    def _wakeup_partitioner(self):
        self._worker_map['raw_data_partitioner'].wakeup()

    def _wakeup_raw_data_fetcher(self):
        self._worker_map['raw_data_batch_fetcher'].wakeup()

    def _dump_finished_tag(self):
        finished_tag_fpath = self._get_finished_tag_fpath()
        with gfile.GFile(finished_tag_fpath, 'w') as fh:
            fh.write('finished')

    def _check_finished_tag(self):
        return gfile.Exists(self._get_finished_tag_fpath())

    def _get_finished_tag_fpath(self):
        return os.path.join(
                self._options.output_dir,
                '_SUCCESS.{:08}'.format(self._options.partitioner_rank_id)
            )

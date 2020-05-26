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
import argparse
from fnmatch import fnmatch
import os
import re
import uuid

import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile

from cityhash import CityHash32 # pylint: disable=no-name-in-module

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common.etcd_client import EtcdClient

from fedlearner.data_join.item_batch_seq_processor import \
        ItemBatch, ItemBatchSeqProcessor
from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.raw_data_visitor import MockRawDataVisitor
from fedlearner.data_join.csv_dict_writer import CsvDictWriter
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
    def __init__(self, etcd, options):
        super(RawDataBatchFetcher, self).__init__(
                options.batch_processor_options.max_flying_item,
            )
        self._raw_data_visitor = MockRawDataVisitor(
                etcd, options.raw_data_options,
                '{}-partitioner-mock-data-source-{:04}'.format(
                        options.partitioner_name,
                        options.partitioner_rank_id
                    ),
                options.input_file_paths
            )
        self._batch_size = options.batch_processor_options.batch_size
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
                    os._exit(-1) # pylint: disable=protected-access
                next_batch.append(item)
                next_index += 1
                if len(next_batch) >= self._batch_size:
                    break
            yield next_batch, self._raw_data_visitor.finished()
        yield None, self._raw_data_visitor.finished()

class RawDataPartitioner(object):
    FileSuffix = '.rd'
    class FileMeta(object):
        def __init__(self, process_index, begin_index, end_index):
            self._process_index = process_index
            self._begin_index = begin_index
            self._end_index = end_index

        @property
        def process_index(self):
            return self._process_index

        @property
        def begin_index(self):
            return self._begin_index

        @property
        def end_index(self):
            return self._end_index

        def __lt__(self, other):
            assert isinstance(other, RawDataPartitioner.FileMeta)
            return self.process_index < other.process_index

        def encode_meta_to_fname(self):
            return '{:08}.{:010}-{:010}{}'.format(
                    self.process_index, self.begin_index,
                    self.end_index, RawDataPartitioner.FileSuffix
                )

        @classmethod
        def decode_meta_from_fname(cls, fname):
            assert fname.endswith(RawDataPartitioner.FileSuffix)
            segs = re.split('\.|-', fname[:-len(RawDataPartitioner.FileSuffix)]) # pylint: disable=anomalous-backslash-in-string
            assert len(segs) == 3
            return RawDataPartitioner.FileMeta(int(segs[0]),
                                               int(segs[1]),
                                               int(segs[2]))

    class OutputFileWriter(object):
        TMP_COUNTER = 0
        def __init__(self, options, partition_id, process_index):
            self._options = options
            self._partition_id = partition_id
            self._process_index = process_index
            self._begin_index = None
            self._end_index = None
            self._writer = None
            self._tmp_fpath = os.path.join(
                    self._options.output_dir,
                    common.partition_repr(self._partition_id),
                    '{}-{}.tmp'.format(str(uuid.uuid1()),
                                       self.TMP_COUNTER)
                )
            self.TMP_COUNTER += 1

        def append_item(self, index, item):
            writer = self._get_output_writer()
            if self._options.output_builder == 'TF_RECORD':
                writer.write(item.tf_record)
            else:
                assert self._options.output_builder == 'CSV_DICT'
                writer.write(item.csv_record)
            if self._begin_index is None:
                self._begin_index = index
            self._end_index = index

        def finish(self):
            meta = None
            if self._writer is not None:
                self._writer.close()
                self._writer = None
                meta = RawDataPartitioner.FileMeta(self._process_index,
                                                   self._begin_index,
                                                   self._end_index)
                fpath = os.path.join(self._options.output_dir,
                                     common.partition_repr(self._partition_id),
                                     meta.encode_meta_to_fname())
                gfile.Rename(self.get_tmp_fpath(), fpath)
            return meta

        def get_tmp_fpath(self):
            return self._tmp_fpath

        def destory(self):
            if self._writer is not None:
                self._writer.close()
                self._writer = None
            if gfile.Exists(self._tmp_fpath):
                gfile.Remove(self._tmp_fpath)

        def __del__(self):
            self.destory()

        def _get_output_writer(self):
            if self._writer is None:
                self._new_writer()
            return self._writer

        def _new_writer(self):
            assert self._writer is None
            if self._options.output_builder == 'TF_RECORD':
                self._writer = tf.io.TFRecordWriter(self._tmp_fpath)
            else:
                assert self._options.output_builder == 'CSV_DICT'
                self._writer = CsvDictWriter(self._tmp_fpath)

    def __init__(self, options, etcd_name, etcd_addrs,
                 etcd_base_dir, use_mock_etcd=False):
        self._options = options
        etcd = EtcdClient(etcd_name, etcd_addrs,
                          etcd_base_dir, use_mock_etcd)
        self._raw_data_batch_fetcher = RawDataBatchFetcher(etcd, options)
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
        iter_round = 0
        next_index = self._get_next_part_index()
        hint_index = None
        bp_options = self._options.batch_processor_options
        signal_round_threhold = bp_options.max_flying_item / \
                bp_options.batch_size // 3
        while not fetch_finished:
            fetch_finished, batch, hint_index = \
                    fetcher.fetch_item_batch_by_index(next_index, hint_index)
            if batch is not None:
                for index, item in enumerate(batch):
                    raw_id = item.raw_id
                    partition_id = CityHash32(raw_id) % \
                            self._options.output_partition_num
                    writer = self._get_file_writer(partition_id)
                    writer.append_item(batch.begin_index+index, item)
                next_index += len(batch)
                iter_round += 1
                if iter_round % signal_round_threhold == 0:
                    self._finish_file_writers()
                    self._set_next_part_index(next_index)
                    hint_index = self._evict_staless_batch(hint_index,
                                                           next_index-1)
                    logging.info("consumed %d items", next_index-1)
                    self._wakeup_raw_data_fetcher()
            elif not fetch_finished:
                hint_index = self._evict_staless_batch(hint_index,
                                                       next_index-1)
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
            writer.destory()
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
                  if f.endswith(RawDataPartitioner.FileSuffix)]
        return [RawDataPartitioner.FileMeta.decode_meta_from_fname(f)
                for f in fnames]

    def _raw_data_batch_fetch_fn(self):
        next_part_index = self._get_next_part_index()
        fetcher = self._raw_data_batch_fetcher
        for batch in fetcher.make_processor(next_part_index):
            logging.debug("fetch batch begin at %d, len %d. wakeup "\
                          "partitioner", batch.begin_index, len(batch))
            self._wakeup_partitioner()

    def _raw_data_batch_fetch_cond(self):
        next_part_index = self._get_next_part_index()
        return self._raw_data_batch_fetcher.need_process(next_part_index)

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

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    logging.basicConfig(format='%(asctime)s %(message)s')
    parser = argparse.ArgumentParser(description='Raw Data Partitioner')
    parser.add_argument('--partitioner_name', type=str, default='test',
                        help='the name of raw data partitioner')
    parser.add_argument('--file_paths', type=str, nargs='+',
                        help='the raw data file appointed by file path')
    parser.add_argument('--input_dir', type=str,
                        help='the raw data file appointed by dir')
    parser.add_argument('--input_file_wildcard', type=str,
                        help='the wildcard filter for input file')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='the directory to store the result of processor')
    parser.add_argument('--output_partition_num', type=int, required=True,
                        help='the output partition number')
    parser.add_argument('--raw_data_iter', type=str, default='CSV_DICT',
                        choices=['TF_RECORD', 'CSV_DICT', 'TF_DATASET'],
                        help='the type for raw data file')
    parser.add_argument('--compressed_type', type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type for raw data')
    parser.add_argument('--read_ahead_size', type=int, default=64<<20,
                        help='the read ahead size for raw data,'
                             'only support CSV DICT')
    parser.add_argument('--tf_eager_mode', action='store_true',
                        help='use the eager_mode for tf')
    parser.add_argument('--output_builder', type=str, default='CSV_DICT',
                        choices=['TF_RECORD', 'CSV_DICT'],
                        help='the builder for ouput file')
    parser.add_argument('--output_item_threshold', type=int, default=1<<18,
                        help='the item threshold for output file')
    parser.add_argument('--raw_data_batch_size', type=int, default=2048,
                        help='the batch size to load raw data')
    parser.add_argument('--max_flying_raw_data', type=int, default=2<<20,
                        help='max flying raw data cached output')
    parser.add_argument('--total_partitioner_num', type=int, default=1,
                        help='the number of partitioner worker for input data')
    parser.add_argument('--partitioner_rank_id', type=int, default=0,
                        help='the rank id of partitioner')
    parser.add_argument('--etcd_name', type=str, default='test_etcd',
                        help='the name of etcd cluster')
    parser.add_argument('--etcd_addrs', type=str, default='localhost:2379',
                        help='the addrs of etcd server')
    parser.add_argument('--etcd_base_dir', type=str, default='fedlearner_test',
                        help='the namespace of etcd key')

    args = parser.parse_args()
    if args.tf_eager_mode:
        tf.enable_eager_execution()
    assert 0 <= args.partitioner_rank_id < args.total_partitioner_num
    all_fpaths = []
    if args.file_paths is not None:
        for fp in args.file_paths:
            all_fpaths.append(fp)
    if args.input_dir is not None:
        all_fpaths += [os.path.join(args.input_dir, f)
                       for f in gfile.ListDirectory(args.input_dir)]
    if args.input_file_wildcard is not None and \
            len(args.input_file_wildcard) > 0:
        all_fpaths = [fpath for fpath in all_fpaths
                      if fnmatch(fpath, args.input_file_wildcard)]
    if len(all_fpaths) == 0:
        raise RuntimeError("no input files for partitioner")
    all_fpaths = list(set(all_fpaths))
    all_fpaths.sort()
    partitioner_num = args.total_partitioner_num
    if partitioner_num > 1:
        origin_file_num = len(all_fpaths)
        all_fpaths = \
            [fpath for fpath in all_fpaths
             if CityHash32(os.path.basename(fpath)) %  partitioner_num == \
                     args.partitioner_rank_id]
        logging.info("Partitioner of rank id %d will process %d/%d "\
                     "input files", args.partitioner_rank_id,
                     len(all_fpaths), origin_file_num)
    partitioner_options = dj_pb.RawDataPartitionerOptions(
            partitioner_name=args.partitioner_name,
            input_file_paths=all_fpaths,
            output_dir=args.output_dir,
            output_partition_num=args.output_partition_num,
            raw_data_options=dj_pb.RawDataOptions(
                raw_data_iter=args.raw_data_iter,
                compressed_type=args.compressed_type,
                read_ahead_size=args.read_ahead_size
            ),
            output_builder=args.output_builder,
            output_item_threshold=args.output_item_threshold,
            partitioner_rank_id=args.partitioner_rank_id,
            batch_processor_options=dj_pb.BatchProcessorOptions(
                batch_size=args.raw_data_batch_size,
                max_flying_item=args.max_flying_raw_data
            )
        )
    partitioner = RawDataPartitioner(partitioner_options, args.etcd_name,
                                     args.etcd_addrs, args.etcd_base_dir)
    logging.info("RawDataPartitioner %s of rank %d launched",
                 partitioner_options.partitioner_name,
                 partitioner_options.partitioner_rank_id)
    partitioner.start_process()
    partitioner.wait_for_finished()
    logging.info("RawDataPartitioner %s of rank %d finished",
                 partitioner_options.partitioner_name,
                 partitioner_options.partitioner_rank_id)

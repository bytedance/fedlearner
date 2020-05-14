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

import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile

from cityhash import CityHash32 # pylint: disable=no-name-in-module

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join.item_batch_seq_processor import \
        ItemBatch, ItemBatchSeqProcessor
from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.raw_data_visitor import BatchRawDataVisitor
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
    def __init__(self, options):
        super(RawDataBatchFetcher, self).__init__(
                options.batch_processor_options.max_flying_item,
            )
        self._raw_data_visitor = BatchRawDataVisitor(
                options.input_file_paths,
                options.raw_data_options
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
    class OutputFileWriter(object):
        def __init__(self, options, partition_id):
            self._options = options
            self._partition_id = partition_id
            self._process_index = 0
            self._writer = None
            self._dumped_item = 0
            self._output_fpaths = []
            self._output_dir = os.path.join(
                    self._options.output_dir,
                    common.partition_repr(self._partition_id)
                )
            if not gfile.Exists(self._output_dir):
                gfile.MakeDirs(self._output_dir)
            assert gfile.IsDirectory(self._output_dir)

        def append_item(self, item):
            writer = self._get_output_writer()
            if self._options.output_builder == 'TF_RECORD':
                writer.write(item.tf_record)
            else:
                assert self._options.output_builder == 'CSV_DICT'
                writer.write(item.csv_record)
            self._dumped_item += 1
            if self._dumped_item >= self._options.output_item_threshold:
                self._finish_writer()

        def finish(self):
            self._finish_writer()

        def get_output_files(self):
            return self._output_fpaths

        def _get_output_writer(self):
            if self._writer is None:
                self._new_writer()
            return self._writer

        def _new_writer(self):
            assert self._writer is None
            fpath = os.path.join(self._output_dir,
                                 str(self._process_index)+'.rd')
            self._output_fpaths.append(fpath)
            if self._options.output_builder == 'TF_RECORD':
                self._writer = tf.io.TFRecordWriter(fpath)
            else:
                assert self._options.output_builder == 'CSV_DICT'
                self._writer = CsvDictWriter(fpath)
            self._dumped_item = 0

        def _finish_writer(self):
            if self._writer is not None:
                self._writer.close()
                self._writer = None
            self._dumped_item = 0
            self._process_index += 1

    def __init__(self, options):
        self._options = options
        self._raw_data_batch_fetcher = RawDataBatchFetcher(options)
        self._fetch_worker = RoutineWorker('raw_data_batch_fetcher',
                                           self._raw_data_batch_fetch_fn,
                                           self._raw_data_batch_fetch_cond, 10)
        self._next_part_index = 0
        self._cond = threading.Condition()
        self._fetch_worker.start_routine()

    def partition(self):
        next_index = 0
        hint_index = 0
        fetch_finished = False
        fetcher = self._raw_data_batch_fetcher
        writers = [RawDataPartitioner.OutputFileWriter(self._options, pid)
                   for pid in range(self._options.output_partition_num)]
        while not fetch_finished:
            fetch_finished, batch, hint_index = \
                    fetcher.fetch_item_batch_by_index(next_index, hint_index)
            if batch is not None:
                for item in batch:
                    raw_id = item.raw_id
                    partition_id = CityHash32(raw_id) % \
                            self._options.output_partition_num
                    writer = writers[partition_id]
                    writer.append_item(item)
                next_index = batch.begin_index + len(batch)
                evict_cnt = fetcher.evict_staless_item_batch(next_index-1)
                hint_index -= evict_cnt
                self._set_next_part_index(next_index)
                self._wakeup_raw_data_fetcher()
            elif not fetch_finished:
                with self._cond:
                    self._cond.wait(1)
        for partition_id, writer in enumerate(writers):
            writer.finish()
            fpaths = writer.get_output_files()
            logging.info("part %d output %d files by partitioner",
                          partition_id, len(fpaths))
            for fpath in fpaths:
                logging.info("%s", fpath)
            logging.info("-----------------------------------")
        self._fetch_worker.stop_routine()

    def _set_next_part_index(self, next_part_index):
        with self._cond:
            self._next_part_index = next_part_index

    def _get_next_part_index(self):
        with self._cond:
            return self._next_part_index

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
        with self._cond:
            self._cond.notify_all()

    def _wakeup_raw_data_fetcher(self):
        self._fetch_worker.wakeup()

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    parser = argparse.ArgumentParser(description='Raw Data Partitioner')
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
    parser.add_argument('--raw_data_iter', type=str, default='TF_RECORD',
                        help='the type for raw data file')
    parser.add_argument('--compressed_type', type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type for raw data')
    parser.add_argument('--tf_eager_mode', action='store_true',
                        help='use the eager_mode for tf')
    parser.add_argument('--output_builder', type=str, default='TF_RECORD',
                        choices=['TF_RECORD', 'CSV_DICT'],
                        help='the builder for ouput file')
    parser.add_argument('--output_item_threshold', type=int, default=1<<18,
                        help='the item threshold for output file')
    parser.add_argument('--raw_data_batch_size', type=int, default=512,
                        help='the batch size to load raw data')
    parser.add_argument('--max_flying_raw_data', type=int, default=65536,
                        help='max flying raw data cached output')

    args = parser.parse_args()
    if args.tf_eager_mode:
        tf.enable_eager_execution()
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
    partitioner_options = dj_pb.RawDataPartitionerOptions(
            input_file_paths=list(set(all_fpaths)),
            output_dir=args.output_dir,
            output_partition_num=args.output_partition_num,
            raw_data_options=dj_pb.RawDataOptions(
                raw_data_iter=args.raw_data_iter,
                compressed_type=args.compressed_type
            ),
            output_builder=args.output_builder,
            output_item_threshold=args.output_item_threshold,
            batch_processor_options=dj_pb.BatchProcessorOptions(
                batch_size=args.raw_data_batch_size,
                max_flying_item=args.max_flying_raw_data
            )
        )
    RawDataPartitioner(partitioner_options).partition()

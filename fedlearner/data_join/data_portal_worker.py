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
import time
import os
from functools import cmp_to_key
import gc
import grpc

import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile

from fedlearner.common import data_portal_service_pb2 as dp_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_portal_service_pb2_grpc as dp_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType
from fedlearner.data_join.raw_data_partitioner import RawDataPartitioner
from fedlearner.data_join import common
from fedlearner.data_join.sort_run_merger import SortRunMerger

class RawDataSortPartitioner(RawDataPartitioner):

    class OutputFileSortWriter(RawDataPartitioner.OutputFileWriter):
        def __init__(self, options, partition_id, process_index):
            super(RawDataSortPartitioner.OutputFileSortWriter, self).__init__(
                    options, partition_id, process_index
                )
            self._buffer = []

        def append_item(self, index, item):
            self._buffer.append(item)
            if self._begin_index is None:
                self._begin_index = index
            self._end_index = index

        def finish(self):
            meta = None
            if len(self._buffer) > 0:
                writer = self._get_output_writer()
                self._sort_buffer()
                for item in self._buffer:
                    writer.write_item(item)
                writer.close()
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
                self._buffer = []
                self._begin_index = None
                self._end_index = None
            return meta

        def _sort_buffer(self):
            self._buffer = sorted(self._buffer, key=cmp_to_key(self.item_cmp))

        @staticmethod
        def item_cmp(a, b):
            if a.event_time < b.event_time:
                return -1
            if a.event_time > b.event_time:
                return 1
            if a.example_id < b.example_id:
                return -1
            if a.example_id > b.example_id:
                return 1
            return 0

    def _get_file_writer(self, partition_id):
        if len(self._flying_writers) == 0:
            self._flying_writers = \
              [RawDataSortPartitioner.OutputFileSortWriter(
                  self._options, pid, self._dumped_process_index+1)
                   for pid in range(self._options.output_partition_num)]
        assert partition_id < len(self._flying_writers)
        return self._flying_writers[partition_id]

class DataPortalWorker(object):
    def __init__(self, options, master_addr, rank_id,
                 kvstore_type, use_mock_etcd=False):
        master_channel = make_insecure_channel(
                master_addr, ChannelType.INTERNAL,
                options=[('grpc.max_send_message_length', 2**31-1),
                         ('grpc.max_receive_message_length', 2**31-1)]
            )
        self._kvstore_type = kvstore_type
        self._rank_id = rank_id
        self._options = options
        self._use_mock_etcd = use_mock_etcd
        self._master_client = dp_grpc.DataPortalMasterServiceStub(
            master_channel)

    def request_new_task(self):
        request = dp_pb.NewTaskRequest()
        request.rank_id = self._rank_id
        while True:
            try:
                return self._master_client.RequestNewTask(request)
            except grpc.RpcError as e:
                logging.warning("Request new task failed, sleep 2 seconds"\
                  " and retry. %s", e)
                time.sleep(2)

    def finish_task(self, partition_id, part_state):
        request = dp_pb.FinishTaskRequest()
        request.rank_id = self._rank_id
        request.partition_id = partition_id
        request.part_state = part_state
        while True:
            try:
                self._master_client.FinishTask(request)
                return
            except grpc.RpcError as e:
                logging.warning("Failed to finish request, sleep 2 seconds" \
                    " and retry. %s", e)
                time.sleep(2)

    def start(self):
        logging.info("Start DataPortal Worker, rank_id:%s", self._rank_id)
        logging.info("kvstore type:%s", self._kvstore_type)
        self.run()

    def _make_partitioner_options(self, task):
        return dj_pb.RawDataPartitionerOptions(
            partitioner_name="{}-rank_{}".format(task.task_name,
                                                 self._rank_id),
            input_file_paths=task.fpaths,
            output_dir=task.output_base_dir,
            output_partition_num=task.output_partition_num,
            partitioner_rank_id=task.partition_id,
            batch_processor_options=self._options.batch_processor_options,
            raw_data_options=self._options.raw_data_options,
            writer_options=self._options.writer_options,
            memory_limit_ratio=self._options.memory_limit_ratio
        )

    def _make_merger_options(self, task):
        return dj_pb.SortRunMergerOptions(
            merger_name="{}-rank_{}".format(task.task_name,
                                            self._rank_id),
            reader_options=dj_pb.RawDataOptions(
                raw_data_iter=self._options.writer_options.output_writer,
                compressed_type=self._options.writer_options.compressed_type,
                read_ahead_size=self._options.merger_read_ahead_size,
                read_batch_size=self._options.merger_read_batch_size
            ),
            writer_options=self._options.writer_options,
            output_file_dir=task.reduce_base_dir,
            partition_id=task.partition_id,
        )

    def _run_map_task(self, task):
        partition_options = self._make_partitioner_options(task)
        data_partitioner = None
        type_repr = ''
        if task.data_portal_type == dp_pb.DataPortalType.Streaming:
            data_partitioner = RawDataSortPartitioner(
                partition_options, task.part_field, self._kvstore_type,
                self._use_mock_etcd
            )
            type_repr = 'streaming'
        else:
            assert task.data_portal_type == dp_pb.DataPortalType.PSI
            data_partitioner = RawDataPartitioner(
                partition_options, task.part_field, self._kvstore_type,
                self._use_mock_etcd
            )
            type_repr = 'psi'
        logging.info("Partitioner rank_id-[%d] start run task %s of type %s "\
                     "for partition %d, input %d files", self._rank_id,
                     partition_options.partitioner_name, type_repr,
                     partition_options.partitioner_rank_id,
                     len(partition_options.input_file_paths))
        data_partitioner.start_process()
        data_partitioner.wait_for_finished()
        logging.info("Partitioner rank_id-[%d] finish run partition task %s "\
                     "for partition %d.", self._rank_id,
                     partition_options.partitioner_name,
                     partition_options.partitioner_rank_id)
        del data_partitioner
        gc.collect()

    def _run_reduce_task(self, task):
        merger_options = self._make_merger_options(task)
        sort_run_merger = SortRunMerger(merger_options, self._merger_comparator)
        input_dir = os.path.join(task.map_base_dir,
                                 common.partition_repr(task.partition_id))
        input_fpaths = [os.path.join(input_dir, f) for f in
                        gfile.ListDirectory(input_dir)
                        if f.endswith(common.RawDataFileSuffix)]
        logging.info("Merger rank_id-[%d] start run task %s for partition "\
                     "%d. input_dir %s, with %d files",
                     self._rank_id, merger_options.merger_name,
                     task.partition_id, task.map_base_dir, len(input_fpaths))
        sort_run_merger.merge_sort_runs(input_fpaths)
        logging.info("Merger rank_id-[%d] finish task %s for "\
                     "partition %d", self._rank_id,
                     merger_options.merger_name, task.partition_id)
        del sort_run_merger
        gc.collect()

    @staticmethod
    def _merger_comparator(a, b):
        if a.event_time != b.event_time:
            return a.event_time < b.event_time
        return a.example_id < b.example_id

    def run(self):
        while True:
            response = self.request_new_task()
            if response.HasField("finished"):
                logging.info("Receive finished response from Master.")
                return
            if response.HasField("map_task"):
                task = response.map_task
                logging.info("Receive map task partition_id:%d, paths:%s",
                             task.partition_id, task.fpaths)
                self._run_map_task(task)
                self.finish_task(task.partition_id, dp_pb.PartState.kIdMap)
                continue
            if response.HasField("reduce_task"):
                task = response.reduce_task
                logging.info("Receive reduce task, partition_id:%d, input"\
                             " dir %s", task.partition_id, task.map_base_dir)
                self._run_reduce_task(task)
                self.finish_task(task.partition_id,
                                 dp_pb.PartState.kEventTimeReduce)
                continue
            if response.HasField("pending"):
                logging.warning("Receive pending response.")
            else:
                logging.warning("The response from master is invalid.")
            time.sleep(2)

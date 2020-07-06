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
import time
import os

from tensorflow.compat.v1 import gfile
import tensorflow as tf

from fedlearner.common import data_portal_service_pb2 as dp_pb
from fedlearner.common import data_portal_service_pb2_grpc as dp_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType
from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.raw_data_partitioner import RawDataPartitioner
from fedlearner.data_join import common
from fedlearner.data_join.merge import Merge
from fedlearner.common.etcd_client import EtcdClient

class RawDataSortPartitioner(RawDataPartitioner):

    class OutputFileSortWriter(object):
        def __init__(self, options, partition_id, process_index):
            self._options = options
            self._partition_id = partition_id
            self._process_index = process_index
            self._begin_index = None
            self._end_index = None
            self._buffer = []
            self._size_bytes = 0
            self._tmp_fpath = common.gen_tmp_fpath(
                    os.path.join(self._options.output_dir,
                                 common.partition_repr(self._partition_id))
                )

        def append_item(self, index, item):
            self._buffer.append(item)
            self._size_bytes += len(item.tf_record)
            if self._begin_index is None:
                self._begin_index = index
            self._end_index = index

            if self._size_bytes >= self._options.output_item_threshold:
                self.dump()

        def dump(self):
            if len(self._buffer) > 0:
                writer = self._get_output_writer()
                self.sort_buffer()
                for item in self._buffer: 
                    writer.write(item.tf_record)
                writer.close()
                meta = RawDataPartitioner.FileMeta(
                  self._options.partitioner_rank_id,
                  self._process_index,
                  self._begin_index,
                  self._end_index)
                fpath = os.path.join(self._options.output_dir,
                  common.partition_repr(self._partition_id),
                  meta.encode_meta_to_fname())
                gfile.Rename(self.get_tmp_fpath(), fpath, True)

                self._buffer = []
                self._begin_index = None
                self._end_index = None
                self._size_bytes = 0
                return meta

        def finish(self):
            meta = self.dump()
            if gfile.Exists(self._tmp_fpath):
                gfile.Remove(self._tmp_fpath)
        
        def get_tmp_fpath(self):
            return self._tmp_fpath

        def sort_buffer(self):
            self._buffer = sorted(self._buffer, key = lambda item: item.event_time)

        def _get_output_writer(self):
            return tf.io.TFRecordWriter(self._tmp_fpath)

    def __init__(self, options, etcd_name, etcd_addrs, 
                 etcd_base_dir, use_mock_etcd=False):
        super(RawDataSortPartitioner, self).__init__(
          options, etcd_name, etcd_addrs, etcd_base_dir, use_mock_etcd)
    
    def _get_file_writer(self, partition_id):
        if len(self._flying_writers) == 0:
            self._flying_writers = \
              [RawDataSortPartitioner.OutputFileSortWriter(
                  self._options, pid, self._dumped_process_index+1)
                   for pid in range(self._options.output_partition_num)]
        assert partition_id < len(self._flying_writers)
        return self._flying_writers[partition_id]

class DataPortalWorkerService(object):
    def __init__(self, options, master_addr, rank_id, etcd_name, 
                 etcd_base_dir, etcd_addrs, use_mock_etcd=False):
        master_channel = make_insecure_channel(
          master_addr, ChannelType.INTERNAL)
        self._etcd_name = etcd_name
        self._etcd_base_dir = etcd_base_dir
        self._etcd_addrs = etcd_addrs
        self._master_client = dp_grpc.DataPortalMasterServiceStub(master_channel)
        self._rank_id = rank_id
        self._started = False
        self._is_stoped = False
        self._raw_data_partitioner = None
        self._merger = None
        self._sort_merger = None
        self._options = options
        self._use_mock_etcd = use_mock_etcd
    
    def request_new_task(self):
        request = dp_pb.NewTaskRequest()
        request.rank_id = self._rank_id
        while True:
            try:
                return self._master_client.RequestNewTask(request)
            except Exception as e:
                logging.warning("Request new task failed, sleep 2 seconds"\
                  " and retry. Exception {}".format(e))
            time.sleep(2)

    def finish_task(self, partition_id):
        request = dp_pb.FinishTaskRequest()
        request.rank_id = self._rank_id
        request.partition_id = partition_id
        while True:
            try:
                self._master_client.FinishTask(request)
                return
            except Exception as e:
                logging.warning("Failed to finish task request, sleep 2 seconds "\
                  "and retry. Exception {}".format(e))
            time.sleep(2)

    def start(self):
        logging.info("Start DataPortal Worker, rank_id:{}".format(self._rank_id))
        logging.info("etcd_name:{} etcd_addr:{} etcd_base_dir:{}".format(self._etcd_name,
            self._etcd_addrs, self._etcd_base_dir))
        self.run()

    def _make_partitioner_options(self, task):
        partitioner_options = self._options.partitioner_options
        partitioner_options.input_file_paths.extend(task.fpaths)
        partitioner_options.output_dir = task.output_base_dir
        partitioner_options.partitioner_name = "raw_data_partitioner-rank_id:{}" \
            .format(self._rank_id)
        partitioner_options.output_partition_num = task.output_partition_num
        partitioner_options.output_builder = "TF_RECORD"
        partitioner_options.partitioner_rank_id = task.partition_id
        return partitioner_options
    
    def _make_merge_options(self, task):
        merge_options = self._options.merge_options
        merge_options.output_builder = "TF_RECORD"
        merge_options.input_dir = task.map_base_dir
        merge_options.input_dir = os.path.join(task.map_base_dir, \
            common.partition_repr(task.partition_id))
        merge_options.output_dir = task.output_base_dir
        merge_options.partition_id = task.partition_id
        merge_options.fpath.extend(gfile.ListDirectory(merge_options.input_dir))
        return merge_options
        
    def _run_map_task(self, task):
        partition_options = self._make_partitioner_options(task)
        self._raw_data_partitioner = RawDataSortPartitioner(
            partition_options, self._etcd_name, self._etcd_addrs, 
            self._etcd_base_dir, self._use_mock_etcd)
        logging.info("RawDataSortPartitioner rank_id:{}, partition_id:{} started."
            .format(self._rank_id, partition_options.partitioner_rank_id))
        self._raw_data_partitioner.start_process()
        self._raw_data_partitioner.wait_for_finished()

    def _run_reduce_task(self, task):
        merge_options = self._make_merge_options(task)
        self._merger = Merge(merge_options, task.partition_id)
        logging.info("Merger rank_id:{} partition_id:{} started."
            .format(self._rank_id, task.partition_id))
        self._merger.generate_output()
    
    def run(self):
        while True:
            response = self.request_new_task()
            if response.HasField("finished"):
                logging.info("Receive finished response from Master.")
                return
            if response.HasField("pending"):
                logging.warning("Receive pending response from Master, sleep 2 seconds "\
                    "and retry.")
                time.sleep(2)
                continue
            if response.HasField("map_task"):
                task = response.map_task
                logging.info("Receive map task, partition_id:{}".format(task.partition_id))
                self._run_map_task(task)
                self.finish_task(task.partition_id)
                continue
            if response.HasField("reduce_task"):
                logging.info("Receive reduce task and running")
                self._run_reduce_task(task)
                self.finish_task(task.partition_id)
                continue

            logging.warning("the response from master is invalid.")
            time.sleep(2)
            
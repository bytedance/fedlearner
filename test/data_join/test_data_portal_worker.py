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

import os
import random
import unittest
import logging

import tensorflow_io
from tensorflow.compat.v1 import gfile
import tensorflow.compat.v1 as tf
tf.enable_eager_execution()

from cityhash import CityHash32

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_portal_service_pb2 as dp_pb
from fedlearner.data_join.data_portal_worker import DataPortalWorker
from fedlearner.data_join.raw_data_iter_impl.tf_record_iter import TfExampleItem
from fedlearner.data_join import common

class TestDataPortalWorker(unittest.TestCase):

    def _get_input_fpath(self, partition_id):
        return "{}/raw_data_partition_{}".format(self._input_dir, partition_id)

    def _generate_one_partition(self, partition_id, example_id, num_examples):
        fpath = self._get_input_fpath(partition_id)
        with tf.io.TFRecordWriter(fpath) as writer:
            for i in range(num_examples):
                example_id += random.randint(1, 5)
                # real_id = example_id.encode("utf-8")
                event_time = 150000000 + random.randint(10000000, 20000000)
                feat = {}
                feat['example_id'] = tf.train.Feature(
                    bytes_list=tf.train.BytesList(value=[str(example_id).encode('utf-8')]))
                feat['raw_id'] = tf.train.Feature(
                    bytes_list=tf.train.BytesList(value=[str(example_id).encode('utf-8')]))
                feat['event_time'] = tf.train.Feature(
                    int64_list=tf.train.Int64List(value=[event_time]))
                example = tf.train.Example(features=tf.train.Features(feature=feat))
                writer.write(example.SerializeToString())
        return example_id


    def _generate_input_data(self):
        self._partition_item_num = 1 << 16
        self._clean_up()
        gfile.MakeDirs(self._input_dir)
        success_flag_fpath = "{}/_SUCCESS".format(self._input_dir)
        example_id = 1000001
        for partition_id in range(self._input_partition_num):
            example_id = self._generate_one_partition(partition_id, example_id, self._partition_item_num)
        
        with gfile.GFile(success_flag_fpath, 'w') as fh:
            fh.write('')

    def _make_portal_worker(self):
        portal_worker_options = dp_pb.DataPortalWorkerOptions(
            raw_data_options=dj_pb.RawDataOptions(
                raw_data_iter="TF_RECORD",
                read_ahead_size=1<<20,
                read_batch_size=128
            ),
            writer_options=dj_pb.WriterOptions(
                output_writer="TF_RECORD"
            ),
            batch_processor_options=dj_pb.BatchProcessorOptions(
                batch_size=128,
                max_flying_item=300000
            ),
            merge_buffer_size=4096,
            merger_read_ahead_size=1000000,
            merger_read_batch_size=128
        )

        self._portal_worker = DataPortalWorker(portal_worker_options,
                                               "localhost:5005", 0,
                                               "test_portal_worker_0",
                                               "portal_worker_0",
                                               "localhost:2379", True)

    def _clean_up(self):
        if gfile.Exists(self._input_dir):
            gfile.DeleteRecursively(self._input_dir)
        if gfile.Exists(self._partition_output_dir):
            gfile.DeleteRecursively(self._partition_output_dir)
        if gfile.Exists(self._merge_output_dir):
            gfile.DeleteRecursively(self._merge_output_dir)

    def _prepare_test(self):
        self._input_dir = './portal_worker_input'
        self._partition_output_dir = './portal_worker_partition_output'
        self._merge_output_dir = './portal_worker_merge_output'
        self._input_partition_num = 4
        self._output_partition_num = 2
        self._generate_input_data()
        self._make_portal_worker()

    def _check_partitioner(self, map_task):
        output_partitions = gfile.ListDirectory(map_task.output_base_dir)
        output_partitions = [x for x in output_partitions if "SUCCESS" not in x]
        self.assertEqual(len(output_partitions), map_task.output_partition_num)
        partition_dirs = ["{}/{}".format(map_task.output_base_dir, x) \
            for x in output_partitions]
        
        total_cnt = 0
        for partition in output_partitions:
            dpath = "{}/{}".format(map_task.output_base_dir, partition)
            partition_id = partition.split("_")[-1]
            partition_id = int(partition_id)
            segments = gfile.ListDirectory(dpath)
            for segment in segments:
                fpath = "{}/{}".format(dpath, segment)
                event_time = 0
                for record in tf.python_io.tf_record_iterator(fpath):
                    tf_item = TfExampleItem(record)
                    self.assertTrue(tf_item.event_time >= event_time, "{}, {}".format(tf_item.event_time, event_time))
                    event_time = tf_item.event_time  ## assert order
                    self.assertEqual(partition_id, CityHash32(tf_item.raw_id) \
                        % map_task.output_partition_num)
                    total_cnt += 1
        self.assertEqual(total_cnt, self._partition_item_num * self._input_partition_num)

    def _check_merge(self, reduce_task):
        dpath = os.path.join(self._merge_output_dir, \
            common.partition_repr(reduce_task.partition_id))
        fpaths = gfile.ListDirectory(dpath)
        fpaths = sorted(fpaths, key = lambda fpath: fpath, reverse = False)
        event_time = 0
        total_cnt = 0
        for fpath in fpaths:
            fpath = os.path.join(dpath, fpath)
            logging.info("check merge path:{}".format(fpath))
            for record in tf.python_io.tf_record_iterator(fpath):
                tf_item = TfExampleItem(record)
                self.assertTrue(tf_item.event_time >= event_time)
                event_time = tf_item.event_time
                total_cnt += 1
        return total_cnt


    def test_portal_worker(self):
        self._prepare_test()
        map_task = dp_pb.MapTask()
        map_task.output_base_dir = self._partition_output_dir
        map_task.output_partition_num = self._output_partition_num
        map_task.partition_id = 0
        map_task.task_name = 'map_part_{}'.format(map_task.partition_id)
        map_task.part_field = 'example_id'
        map_task.data_portal_type = dp_pb.DataPortalType.Streaming
        for partition_id in range(self._input_partition_num):
            map_task.fpaths.append(self._get_input_fpath(partition_id))

        # partitioner
        task = dp_pb.NewTaskResponse()
        task.map_task.CopyFrom(map_task)
        self._portal_worker._run_map_task(task.map_task)

        self._check_partitioner(task.map_task)

        # merge
        total_cnt = 0
        for partition_id in range(self._output_partition_num):
            reduce_task = dp_pb.ReduceTask()
            reduce_task.map_base_dir = self._partition_output_dir
            reduce_task.reduce_base_dir = self._merge_output_dir
            reduce_task.partition_id = partition_id
            reduce_task.task_name = 'reduce_part_{}'.format(partition_id)
            self._portal_worker._run_reduce_task(reduce_task)
            total_cnt += self._check_merge(reduce_task)

        self.assertEqual(total_cnt, self._partition_item_num * self._input_partition_num)
        self._clean_up()

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    logging.basicConfig(format="%(asctime)s %(filename)s "\
                               "%(lineno)s %(levelname)s - %(message)s")
    unittest.main()



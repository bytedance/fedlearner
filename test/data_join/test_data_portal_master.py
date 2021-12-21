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
import time
import unittest
import logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from google.protobuf import text_format
import tensorflow_io
from tensorflow.compat.v1 import gfile
from fnmatch import fnmatch

import grpc
from google.protobuf import text_format, empty_pb2

from fedlearner.data_join import data_join_master, common
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_portal_service_pb2 as dp_pb
from fedlearner.common import data_portal_service_pb2_grpc as dp_grpc
from fedlearner.common.db_client import DBClient
from fedlearner.proxy.channel import make_insecure_channel, ChannelType
from fedlearner.data_join.data_portal_master import DataPortalMasterService

class DataPortalMaster(unittest.TestCase):
    def test_api(self):
        logging.getLogger().setLevel(logging.DEBUG)
        kvstore_type = 'etcd'
        db_base_dir = 'dp_test'
        os.environ['ETCD_BASE_DIR'] = db_base_dir
        data_portal_name = 'test_data_source'
        kvstore = DBClient(kvstore_type, True)
        kvstore.delete_prefix(db_base_dir)
        portal_input_base_dir='./portal_upload_dir'
        portal_output_base_dir='./portal_output_dir'
        raw_data_publish_dir = 'raw_data_publish_dir'
        portal_manifest = dp_pb.DataPortalManifest(
                name=data_portal_name,
                data_portal_type=dp_pb.DataPortalType.Streaming,
                output_partition_num=4,
                input_file_wildcard="*.done",
                input_base_dir=portal_input_base_dir,
                output_base_dir=portal_output_base_dir,
                raw_data_publish_dir=raw_data_publish_dir,
                processing_job_id=-1,
                next_job_id=0
            )
        kvstore.set_data(common.portal_kvstore_base_dir(data_portal_name),
                      text_format.MessageToString(portal_manifest))
        if gfile.Exists(portal_input_base_dir):
            gfile.DeleteRecursively(portal_input_base_dir)
        gfile.MakeDirs(portal_input_base_dir)
        all_fnames = ['1001/{}.done'.format(i) for i in range(100)]
        all_fnames.append('{}.xx'.format(100))
        all_fnames.append('1001/_SUCCESS')
        for fname in all_fnames:
            fpath = os.path.join(portal_input_base_dir, fname)
            gfile.MakeDirs(os.path.dirname(fpath))
            with gfile.Open(fpath, "w") as f:
                f.write('xxx')
        portal_master_addr = 'localhost:4061'
        portal_options = dp_pb.DataPotraMasterlOptions(
                use_mock_etcd=True,
                long_running=False,
                check_success_tag=True,
            )
        data_portal_master = DataPortalMasterService(
                int(portal_master_addr.split(':')[1]),
                data_portal_name, kvstore_type,
                portal_options
            )
        data_portal_master.start()

        channel = make_insecure_channel(portal_master_addr, ChannelType.INTERNAL)
        portal_master_cli = dp_grpc.DataPortalMasterServiceStub(channel)
        recv_manifest = portal_master_cli.GetDataPortalManifest(empty_pb2.Empty())
        self.assertEqual(recv_manifest.name, portal_manifest.name)
        self.assertEqual(recv_manifest.data_portal_type, portal_manifest.data_portal_type)
        self.assertEqual(recv_manifest.output_partition_num, portal_manifest.output_partition_num)
        self.assertEqual(recv_manifest.input_file_wildcard, portal_manifest.input_file_wildcard)
        self.assertEqual(recv_manifest.input_base_dir, portal_manifest.input_base_dir)
        self.assertEqual(recv_manifest.output_base_dir, portal_manifest.output_base_dir)
        self.assertEqual(recv_manifest.raw_data_publish_dir, portal_manifest.raw_data_publish_dir)
        self.assertEqual(recv_manifest.next_job_id, 1)
        self.assertEqual(recv_manifest.processing_job_id, 0)
        self._check_portal_job(kvstore, all_fnames, portal_manifest, 0)
        mapped_partition = set()
        task_0 = portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=0))
        task_0_1 = portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=0))
        self.assertEqual(task_0, task_0_1)
        self.assertTrue(task_0.HasField('map_task'))
        mapped_partition.add(task_0.map_task.partition_id)
        self._check_map_task(task_0.map_task, all_fnames,
                             task_0.map_task.partition_id,
                             portal_manifest)
        portal_master_cli.FinishTask(dp_pb.FinishTaskRequest(
            rank_id=0, partition_id=task_0.map_task.partition_id,
            part_state=dp_pb.PartState.kIdMap)
        )
        task_1 = portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=0))
        self.assertTrue(task_1.HasField('map_task'))
        mapped_partition.add(task_1.map_task.partition_id)
        self._check_map_task(task_1.map_task, all_fnames,
                             task_1.map_task.partition_id,
                             portal_manifest)

        task_2 = portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=1))
        self.assertTrue(task_2.HasField('map_task'))
        mapped_partition.add(task_2.map_task.partition_id)
        self._check_map_task(task_2.map_task, all_fnames,
                             task_2.map_task.partition_id,
                             portal_manifest)

        task_3 = portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=2))
        self.assertTrue(task_3.HasField('map_task'))
        mapped_partition.add(task_3.map_task.partition_id)
        self._check_map_task(task_3.map_task, all_fnames,
                             task_3.map_task.partition_id,
                             portal_manifest)

        self.assertEqual(len(mapped_partition), portal_manifest.output_partition_num)

        portal_master_cli.FinishTask(dp_pb.FinishTaskRequest(
            rank_id=0, partition_id=task_1.map_task.partition_id,
            part_state=dp_pb.PartState.kIdMap)
        )

        pending_1 = portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=4))
        self.assertTrue(pending_1.HasField('pending'))
        pending_2 = portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=3))
        self.assertTrue(pending_2.HasField('pending'))

        portal_master_cli.FinishTask(dp_pb.FinishTaskRequest(
            rank_id=1, partition_id=task_2.map_task.partition_id,
            part_state=dp_pb.PartState.kIdMap)
        )

        portal_master_cli.FinishTask(dp_pb.FinishTaskRequest(
            rank_id=2, partition_id=task_3.map_task.partition_id,
            part_state=dp_pb.PartState.kIdMap)
        )

        reduce_partition = set()
        task_4 = portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=0))
        task_4_1 = portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=0))
        self.assertEqual(task_4, task_4_1)
        self.assertTrue(task_4.HasField('reduce_task'))
        reduce_partition.add(task_4.reduce_task.partition_id)
        self._check_reduce_task(task_4.reduce_task,
                                task_4.reduce_task.partition_id,
                                portal_manifest)
        task_5 = portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=1))
        self.assertTrue(task_5.HasField('reduce_task'))
        reduce_partition.add(task_5.reduce_task.partition_id)
        self._check_reduce_task(task_5.reduce_task,
                                task_5.reduce_task.partition_id,
                                portal_manifest)
        task_6 = portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=2))
        self.assertTrue(task_6.HasField('reduce_task'))
        reduce_partition.add(task_6.reduce_task.partition_id)
        self._check_reduce_task(task_6.reduce_task,
                                task_6.reduce_task.partition_id,
                                portal_manifest)
        task_7= portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=3))
        self.assertTrue(task_7.HasField('reduce_task'))
        reduce_partition.add(task_7.reduce_task.partition_id)
        self.assertEqual(len(reduce_partition), 4)
        self._check_reduce_task(task_7.reduce_task,
                                task_7.reduce_task.partition_id,
                                portal_manifest)

        task_8= portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=5))
        self.assertTrue(task_8.HasField('pending'))

        portal_master_cli.FinishTask(dp_pb.FinishTaskRequest(
            rank_id=0, partition_id=task_4.reduce_task.partition_id,
            part_state=dp_pb.PartState.kEventTimeReduce)
        )
        portal_master_cli.FinishTask(dp_pb.FinishTaskRequest(
            rank_id=1, partition_id=task_5.reduce_task.partition_id,
            part_state=dp_pb.PartState.kEventTimeReduce)
        )
        portal_master_cli.FinishTask(dp_pb.FinishTaskRequest(
            rank_id=2, partition_id=task_6.reduce_task.partition_id,
            part_state=dp_pb.PartState.kEventTimeReduce)
        )
        portal_master_cli.FinishTask(dp_pb.FinishTaskRequest(
            rank_id=3, partition_id=task_7.reduce_task.partition_id,
            part_state=dp_pb.PartState.kEventTimeReduce)
        )

        time.sleep(31)
        task_9= portal_master_cli.RequestNewTask(dp_pb.NewTaskRequest(rank_id=5))
        self.assertTrue(task_9.HasField('finished'))

        data_portal_master.stop()
        gfile.DeleteRecursively(portal_input_base_dir)

    def _check_portal_job(self, kvstore, fnames, portal_manifest, job_id):
        kvstore_key = common.portal_job_kvstore_key(portal_manifest.name, job_id)
        data = kvstore.get_data(kvstore_key)
        self.assertIsNotNone(data)
        portal_job = text_format.Parse(data, dp_pb.DataPortalJob())
        self.assertEqual(job_id, portal_job.job_id)
        self.assertFalse(portal_job.finished)
        fnames.sort()
        fpaths = [os.path.join(portal_manifest.input_base_dir, f) for f in fnames 
                  if fnmatch(f, portal_manifest.input_file_wildcard)]
        self.assertEqual(len(fpaths), len(portal_job.fpaths))
        for index, fpath in enumerate(fpaths):
            self.assertEqual(fpath, portal_job.fpaths[index])

    def _check_map_task(self, map_task, fnames, partition_id, portal_manifest):
        self.assertEqual(map_task.output_partition_num, portal_manifest.output_partition_num)
        fnames.sort()
        fpaths = [os.path.join(portal_manifest.input_base_dir, f) for f in fnames 
                  if (fnmatch(f, portal_manifest.input_file_wildcard) and
                          hash(os.path.join(portal_manifest.input_base_dir, f)) %
                            map_task.output_partition_num == partition_id)]
        self.assertEqual(len(fpaths), len(map_task.fpaths))
        for index, fpath in enumerate(fpaths):
            self.assertEqual(fpath, map_task.fpaths[index])
        self.assertEqual(map_task.output_base_dir,
                         common.portal_map_output_dir(portal_manifest.output_base_dir, 0))

    def _check_reduce_task(self, reduce_task, partition_id, portal_manifest):
        self.assertEqual(reduce_task.partition_id, partition_id)
        self.assertEqual(reduce_task.map_base_dir,
                         common.portal_map_output_dir(portal_manifest.output_base_dir, 0))
        self.assertEqual(reduce_task.reduce_base_dir,
                         common.portal_reduce_output_dir(portal_manifest.output_base_dir, 0))


if __name__ == '__main__':
        unittest.main()

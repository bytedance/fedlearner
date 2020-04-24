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
import logging
from os import listdir
from os.path import isfile, join
import time
import random
from datetime import datetime, timedelta
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import unittest
import tensorflow.compat.v1 as tf
import numpy as np
from tensorflow.compat.v1 import gfile
from google.protobuf import text_format, empty_pb2, timestamp_pb2

import grpc

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.common.etcd_client import EtcdClient

from fedlearner.proxy.channel import make_insecure_channel, ChannelType
from fedlearner.data_join import (
    data_block_manager, common, data_join_master,
    data_join_worker, data_join_portal, raw_data_controller
)

class DataJoinPortal(unittest.TestCase):
    def _setUpEtcd(self):
        self._etcd_name = 'test_etcd'
        self._etcd_addrs = 'localhost:2379'
        self._etcd_base_dir_l = 'byefl_l'
        self._etcd_base_dir_f= 'byefl_f'
        self._etcd_l = EtcdClient(self._etcd_name, self._etcd_addrs,
                                  self._etcd_base_dir_l, True)
        self._etcd_f = EtcdClient(self._etcd_name, self._etcd_addrs,
                                  self._etcd_base_dir_f, True)

    def _setUpDataSource(self):
        self._data_source_name = 'test_data_source'
        self._etcd_l.delete_prefix(self._data_source_name)
        self._etcd_f.delete_prefix(self._data_source_name)
        self._data_source_l = common_pb.DataSource()
        self._data_source_l.role = common_pb.FLRole.Leader
        self._data_source_l.state = common_pb.DataSourceState.Init
        self._data_source_l.data_block_dir = "./data_block_l"
        self._data_source_l.raw_data_dir = "./raw_data_l"
        self._data_source_l.example_dumped_dir = "./example_dumped_l"
        self._data_source_f = common_pb.DataSource()
        self._data_source_f.role = common_pb.FLRole.Follower
        self._data_source_f.state = common_pb.DataSourceState.Init
        self._data_source_f.data_block_dir = "./data_block_f"
        self._data_source_f.raw_data_dir = "./raw_data_f"
        self._data_source_f.example_dumped_dir = "./example_dumped_f"
        data_source_meta = common_pb.DataSourceMeta()
        data_source_meta.name = self._data_source_name
        data_source_meta.partition_num = 2
        data_source_meta.start_time = 0
        data_source_meta.end_time = 100000000
        self._data_source_l.data_source_meta.MergeFrom(data_source_meta)
        self._data_source_f.data_source_meta.MergeFrom(data_source_meta)
        common.commit_data_source(self._etcd_l, self._data_source_l)
        common.commit_data_source(self._etcd_f, self._data_source_f)

    def _setUpPortalManifest(self):
        self._portal_name = 'test_portal'
        self._etcd_l.delete_prefix(self._portal_name)
        self._etcd_f.delete_prefix(self._portal_name)
        self._portal_manifest_l = common_pb.DataJoinPortalManifest(
                name=self._portal_name,
                input_partition_num=4,
                output_partition_num=2,
                input_data_base_dir='./portal_input_l',
                output_data_base_dir='./portal_output_l',
                begin_timestamp=common.trim_timestamp_by_hourly(
                    common.convert_datetime_to_timestamp(datetime.now())
                )
            )
        self._portal_manifest_f = common_pb.DataJoinPortalManifest(
                name=self._portal_name,
                input_partition_num=2,
                output_partition_num=2,
                input_data_base_dir='./portal_input_f',
                output_data_base_dir='./portal_output_f',
                begin_timestamp=common.trim_timestamp_by_hourly(
                    common.convert_datetime_to_timestamp(datetime.now())
                )
            )
        common.commit_portal_manifest(self._etcd_l, self._portal_manifest_l)
        common.commit_portal_manifest(self._etcd_f, self._portal_manifest_f)

    def _launch_masters(self):
        self._master_addr_l = 'localhost:4061'
        self._master_addr_f = 'localhost:4062'
        master_options = dj_pb.DataJoinMasterOptions(use_mock_etcd=True)
        self._master_l = data_join_master.DataJoinMasterService(
                int(self._master_addr_l.split(':')[1]), self._master_addr_f,
                self._data_source_name, self._etcd_name, self._etcd_base_dir_l,
                self._etcd_addrs, master_options 
            )
        self._master_f = data_join_master.DataJoinMasterService(
                int(self._master_addr_f.split(':')[1]), self._master_addr_l,
                self._data_source_name, self._etcd_name, self._etcd_base_dir_f,
                self._etcd_addrs, master_options 
            )
        self._master_f.start()
        self._master_l.start()
        channel_l = make_insecure_channel(self._master_addr_l, ChannelType.INTERNAL)
        self._master_client_l = dj_grpc.DataJoinMasterServiceStub(channel_l)
        channel_f = make_insecure_channel(self._master_addr_f, ChannelType.INTERNAL)
        self._master_client_f = dj_grpc.DataJoinMasterServiceStub(channel_f)

        while True:
            req_l = dj_pb.DataSourceRequest(
                    data_source_meta=self._data_source_l.data_source_meta
                )
            req_f = dj_pb.DataSourceRequest(
                    data_source_meta=self._data_source_f.data_source_meta
                )
            dss_l = self._master_client_l.GetDataSourceStatus(req_l)
            dss_f = self._master_client_f.GetDataSourceStatus(req_f)
            self.assertEqual(dss_l.role, common_pb.FLRole.Leader)
            self.assertEqual(dss_f.role, common_pb.FLRole.Follower)
            if dss_l.state == common_pb.DataSourceState.Processing and \
                    dss_f.state == common_pb.DataSourceState.Processing:
                break
            else:
                time.sleep(2)
        logging.info("masters turn into Processing state")

    def _launch_workers(self):
        worker_options = dj_pb.DataJoinWorkerOptions(
                use_mock_etcd=True,
                raw_data_options=dj_pb.RawDataOptions(
                    raw_data_iter='TF_RECORD',
                    compressed_type=''
                ),
                example_id_dump_options=dj_pb.ExampleIdDumpOptions(
                    example_id_dump_interval=1,
                    example_id_dump_threshold=1024
                ),
                example_joiner_options=dj_pb.ExampleJoinerOptions(
                    example_joiner='STREAM_JOINER',
                    min_matching_window=64,
                    max_matching_window=256,
                    data_block_dump_interval=30,
                    data_block_dump_threshold=1000
                ),
                example_id_batch_options=dj_pb.ExampleIdBatchOptions(
                    example_id_batch_size=1024,
                    max_flying_example_id=4096
                )
            )
        self._worker_addrs_l = ['localhost:4161', 'localhost:4162']
        self._worker_addrs_f = ['localhost:5161', 'localhost:5162']
        self._workers_l = []
        self._workers_f = []
        for rank_id in range(2):
            worker_addr_l = self._worker_addrs_l[rank_id]
            worker_addr_f = self._worker_addrs_f[rank_id]
            self._workers_l.append(data_join_worker.DataJoinWorkerService(
                int(worker_addr_l.split(':')[1]),
                worker_addr_f, self._master_addr_l, rank_id,
                self._etcd_name, self._etcd_base_dir_l,
                self._etcd_addrs, worker_options))
            self._workers_f.append(data_join_worker.DataJoinWorkerService(
                int(worker_addr_f.split(':')[1]),
                worker_addr_l, self._master_addr_f, rank_id,
                self._etcd_name, self._etcd_base_dir_f,
                self._etcd_addrs, worker_options))
        for w in self._workers_l:
            w.start()
        for w in self._workers_f:
            w.start()

    def _launch_portals(self):
        portal_options = dj_pb.DataJoinPotralOptions(
                example_validator=dj_pb.ExampleValidatorOptions(
                    example_validator='EXAMPLE_VALIDATOR',
                    validate_event_time=True
                ),
                reducer_buffer_size=1024,
                raw_data_options=dj_pb.RawDataOptions(
                    raw_data_iter='TF_RECORD',
                    compressed_type=''
                ),
                downstream_data_source_masters=[self._master_addr_l],
                use_mock_etcd=True
            )
        self._portal_l = data_join_portal.DataJoinPortal(
                self._portal_name, self._etcd_name,
                self._etcd_addrs, self._etcd_base_dir_l,
                portal_options
            )
        portal_options.downstream_data_source_masters[0] = self._master_addr_f

        self._portal_f = data_join_portal.DataJoinPortal(
                self._portal_name, self._etcd_name,
                self._etcd_addrs, self._etcd_base_dir_f,
                portal_options
            )
        self._portal_l.start()
        self._portal_f.start()

    def _remove_existed_dir(self):
        if gfile.Exists(self._portal_manifest_l.input_data_base_dir):
            gfile.DeleteRecursively(self._portal_manifest_l.input_data_base_dir)
        if gfile.Exists(self._portal_manifest_l.output_data_base_dir):
            gfile.DeleteRecursively(self._portal_manifest_l.output_data_base_dir)
        if gfile.Exists(self._portal_manifest_f.input_data_base_dir):
            gfile.DeleteRecursively(self._portal_manifest_f.input_data_base_dir)
        if gfile.Exists(self._portal_manifest_f.output_data_base_dir):
            gfile.DeleteRecursively(self._portal_manifest_f.output_data_base_dir)
        if gfile.Exists(self._data_source_l.data_block_dir):
            gfile.DeleteRecursively(self._data_source_l.data_block_dir)
        if gfile.Exists(self._data_source_l.raw_data_dir):
            gfile.DeleteRecursively(self._data_source_l.raw_data_dir)
        if gfile.Exists(self._data_source_l.example_dumped_dir):
            gfile.DeleteRecursively(self._data_source_l.example_dumped_dir)
        if gfile.Exists(self._data_source_f.data_block_dir):
            gfile.DeleteRecursively(self._data_source_f.data_block_dir)
        if gfile.Exists(self._data_source_f.raw_data_dir):
            gfile.DeleteRecursively(self._data_source_f.raw_data_dir)
        if gfile.Exists(self._data_source_f.example_dumped_dir):
            gfile.DeleteRecursively(self._data_source_f.example_dumped_dir)

    def _generate_portal_input_data(self, date_time, event_time_filter,
                                    start_index, total_item_num, portal_manifest):
        self.assertEqual(total_item_num % portal_manifest.input_partition_num, 0)
        item_step = portal_manifest.input_partition_num
        for partition_id in range(portal_manifest.input_partition_num):
            cands = list(range(partition_id, total_item_num, item_step))
            for i in range(len(cands)):
                if random.randint(1, 4) > 1:
                    continue
                a = random.randint(i-16, i+16)
                b = random.randint(i-16, i+16)
                if a < 0:
                    a = 0
                if a >= len(cands):
                    a = len(cands) - 1
                if b < 0:
                    b = 0
                if b >= len(cands):
                    b = len(cands) - 1
                if abs(cands[a]//item_step-b) <= 16 and abs(cands[b]//item_step-a) <= 16:
                    cands[a], cands[b] = cands[b], cands[a]
            fpath = common.encode_portal_hourly_fpath(
                    portal_manifest.input_data_base_dir,
                    date_time, partition_id
                )
            if not gfile.Exists(os.path.dirname(fpath)):
                gfile.MakeDirs(os.path.dirname(fpath))
            with tf.io.TFRecordWriter(fpath) as writer:
                for lid in cands:
                    real_id = lid + start_index
                    feat = {}
                    example_id = '{}'.format(real_id).encode()
                    feat['example_id'] = tf.train.Feature(
                            bytes_list=tf.train.BytesList(value=[example_id])
                        )
                    # if test the basic example_validator for invalid event time
                    if real_id == 0 or not event_time_filter(real_id):
                        event_time = 150000000 + real_id
                        feat['event_time'] = tf.train.Feature(
                                int64_list=tf.train.Int64List(value=[event_time])
                            )
                    example = tf.train.Example(features=tf.train.Features(feature=feat))
                    writer.write(example.SerializeToString())
        succ_tag_fpath = common.encode_portal_hourly_finish_tag(
                portal_manifest.input_data_base_dir, date_time
            )
        with gfile.GFile(succ_tag_fpath, 'w') as fh:
            fh.write('')


    def setUp(self):
        self._setUpEtcd()
        self._setUpDataSource()
        self._setUpPortalManifest()
        self._remove_existed_dir()
        self._item_num_l = 0
        self._event_time_filter_l = lambda x : x % 877 == 0
        self._dt_l = common.convert_timestamp_to_datetime(
                self._portal_manifest_l.begin_timestamp
            )
        for i in range(4):
            if i == 1:
                self._missing_datetime_l = self._dt_l
                self._missing_start_index_l = self._item_num_l
                self._missing_item_cnt_l = 1 << 13
                self._item_num_l += self._missing_item_cnt_l 
            else:
                self._generate_portal_input_data(
                        self._dt_l, self._event_time_filter_l,
                        self._item_num_l, 1 << 13, self._portal_manifest_l
                    )
                self._item_num_l += 1 << 13
            self._dt_l += timedelta(hours=1)
        self._item_num_f = 0
        self._event_time_filter_f = lambda x : x % 907 == 0
        self._dt_f = common.convert_timestamp_to_datetime(
                self._portal_manifest_f.begin_timestamp
            )
        for i in range(5):
            if i == 2:
                self._missing_datetime_f = self._dt_f
                self._missing_start_index_f = self._item_num_f
                self._missing_item_cnt_f = 1 << 13
            else:
                self._generate_portal_input_data(
                        self._dt_f, self._event_time_filter_f,
                        self._item_num_f, 1 << 13, self._portal_manifest_f
                    )
            self._item_num_f += 1 << 13
            self._dt_f += timedelta(hours=1)

        self._launch_masters()
        self._launch_workers()
        self._launch_portals()

    def _stop_workers(self):
        for w in self._workers_f:
            w.stop()
        for w in self._workers_l:
            w.stop()

    def _stop_masters(self):
        self._master_f.stop()
        self._master_l.stop()

    def _stop_portals(self):
        self._portal_f.stop()
        self._portal_l.stop()


    def _wait_timestamp(self, target_l, target_f):
        while True:
            min_datetime_l = None
            min_datetime_f = None
            for pid in range(self._data_source_f.data_source_meta.partition_num):
                req_l = dj_pb.RawDataRequest(
                        partition_id=pid,
                        data_source_meta=self._data_source_l.data_source_meta
                    )
                req_f = dj_pb.RawDataRequest(
                        partition_id=pid,
                        data_source_meta=self._data_source_f.data_source_meta
                    )
                rsp_l = self._master_client_l.GetRawDataLatestTimeStamp(req_l)
                rsp_f = self._master_client_f.GetRawDataLatestTimeStamp(req_f)
                datetime_l = common.convert_timestamp_to_datetime(rsp_l.timestamp)
                datetime_f = common.convert_timestamp_to_datetime(rsp_f.timestamp)
                if min_datetime_l is None or min_datetime_l > datetime_l:
                    min_datetime_l = datetime_l
                if min_datetime_f is None or min_datetime_f > datetime_f:
                    min_datetime_f = datetime_f
            if min_datetime_l >= target_l and min_datetime_f >= target_f:
                break
            else:
                time.sleep(2)

    def test_all_pipeline(self):
        self._wait_timestamp(self._missing_datetime_l-timedelta(hours=1),
                             self._missing_datetime_f-timedelta(hours=1))
        self._generate_portal_input_data(self._missing_datetime_l,
                                         self._event_time_filter_l,
                                         self._missing_start_index_l,
                                         1 << 13, self._portal_manifest_l)
        self._generate_portal_input_data(self._missing_datetime_f,
                                         self._event_time_filter_f,
                                         self._missing_start_index_f,
                                         1 << 13, self._portal_manifest_f)
        self._wait_timestamp(self._dt_l-timedelta(hours=1),
                             self._dt_f-timedelta(hours=1))
        self._generate_portal_input_data(self._dt_l,
                                         self._event_time_filter_l,
                                         self._item_num_l, 1 << 13,
                                         self._portal_manifest_l)
        self._dt_l += timedelta(hours=1)
        self.assertEqual(self._dt_f, self._dt_l)
        self._wait_timestamp(self._dt_l-timedelta(hours=1),
                             self._dt_f-timedelta(hours=1))
        data_source_l = self._master_client_l.GetDataSource(empty_pb2.Empty())
        data_source_f = self._master_client_f.GetDataSource(empty_pb2.Empty())
        rd_ctl_l = raw_data_controller.RawDataController(data_source_l,
                                                         self._master_client_l)
        rd_ctl_f = raw_data_controller.RawDataController(data_source_f,
                                                         self._master_client_f)
        for partition_id in range(data_source_l.data_source_meta.partition_num):
            rd_ctl_l.finish_raw_data(partition_id)
            rd_ctl_f.finish_raw_data(partition_id)

        while True:
            req_l = dj_pb.DataSourceRequest(
                    data_source_meta=self._data_source_l.data_source_meta
                )
            req_f = dj_pb.DataSourceRequest(
                    data_source_meta=self._data_source_f.data_source_meta
                )
            dss_l = self._master_client_l.GetDataSourceStatus(req_l)
            dss_f = self._master_client_f.GetDataSourceStatus(req_f)
            self.assertEqual(dss_l.role, common_pb.FLRole.Leader)
            self.assertEqual(dss_f.role, common_pb.FLRole.Follower)
            if dss_l.state == common_pb.DataSourceState.Finished and \
                    dss_f.state == common_pb.DataSourceState.Finished:
                break
            else:
                time.sleep(2)
        logging.info("masters turn into Finished state")

    def tearDown(self):
        self._stop_portals()
        self._stop_masters()
        self._stop_workers()
        self._remove_existed_dir()

if __name__ == '__main__':
        unittest.main()

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
from os import listdir
from os.path import isfile, join
import time
import random
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import unittest
import tensorflow.compat.v1 as tf
import numpy as np
from tensorflow.compat.v1 import gfile
from google.protobuf import text_format, empty_pb2

import grpc

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.common.etcd_client import EtcdClient

from fedlearner.proxy.channel import make_insecure_channel, ChannelType
from fedlearner.data_join import (
    data_block_manager, common,
    data_join_master, data_join_worker,
    raw_data_visitor, raw_data_controller
)

class DataJoinWorker(unittest.TestCase):
    def setUp(self):
        etcd_name = 'test_etcd'
        etcd_addrs = 'localhost:2379'
        etcd_base_dir_l = 'byefl_l'
        etcd_base_dir_f= 'byefl_f'
        data_source_name = 'test_data_source'
        etcd_l = EtcdClient(etcd_name, etcd_addrs, etcd_base_dir_l, True)
        etcd_f = EtcdClient(etcd_name, etcd_addrs, etcd_base_dir_f, True)
        etcd_l.delete_prefix(data_source_name)
        etcd_f.delete_prefix(data_source_name)
        data_source_l = common_pb.DataSource()
        data_source_l.role = common_pb.FLRole.Leader
        data_source_l.state = common_pb.DataSourceState.Init
        data_source_l.data_block_dir = "./data_block_l"
        data_source_l.raw_data_dir = "./raw_data_l"
        data_source_l.example_dumped_dir = "./example_dumped_l"
        data_source_f = common_pb.DataSource()
        data_source_f.role = common_pb.FLRole.Follower
        data_source_f.state = common_pb.DataSourceState.Init
        data_source_f.data_block_dir = "./data_block_f"
        data_source_f.raw_data_dir = "./raw_data_f"
        data_source_f.example_dumped_dir = "./example_dumped_f"
        data_source_meta = common_pb.DataSourceMeta()
        data_source_meta.name = data_source_name
        data_source_meta.partition_num = 2
        data_source_meta.start_time = 0
        data_source_meta.end_time = 100000000
        data_source_l.data_source_meta.MergeFrom(data_source_meta)
        etcd_l.set_data(os.path.join(data_source_name, 'master'),
                        text_format.MessageToString(data_source_l))
        data_source_f.data_source_meta.MergeFrom(data_source_meta)
        etcd_f.set_data(os.path.join(data_source_name, 'master'),
                        text_format.MessageToString(data_source_f))
        master_options = dj_pb.DataJoinMasterOptions(use_mock_etcd=True)

        master_addr_l = 'localhost:4061'
        master_addr_f = 'localhost:4062'
        master_l = data_join_master.DataJoinMasterService(
                int(master_addr_l.split(':')[1]), master_addr_f,
                data_source_name, etcd_name, etcd_base_dir_l,
                etcd_addrs, master_options,
            )
        master_l.start()
        master_f = data_join_master.DataJoinMasterService(
                int(master_addr_f.split(':')[1]), master_addr_l,
                data_source_name, etcd_name, etcd_base_dir_f,
                etcd_addrs, master_options
            )
        master_f.start()
        channel_l = make_insecure_channel(master_addr_l, ChannelType.INTERNAL)
        master_client_l = dj_grpc.DataJoinMasterServiceStub(channel_l)
        channel_f = make_insecure_channel(master_addr_f, ChannelType.INTERNAL)
        master_client_f = dj_grpc.DataJoinMasterServiceStub(channel_f)

        while True:
            req_l = dj_pb.DataSourceRequest(
                    data_source_meta=data_source_l.data_source_meta
                )
            req_f = dj_pb.DataSourceRequest(
                    data_source_meta=data_source_f.data_source_meta
                )
            dss_l = master_client_l.GetDataSourceStatus(req_l)
            dss_f = master_client_f.GetDataSourceStatus(req_f)
            self.assertEqual(dss_l.role, common_pb.FLRole.Leader)
            self.assertEqual(dss_f.role, common_pb.FLRole.Follower)
            if dss_l.state == common_pb.DataSourceState.Processing and \
                    dss_f.state == common_pb.DataSourceState.Processing:
                break
            else:
                time.sleep(2)

        self.master_client_l = master_client_l
        self.master_client_f = master_client_f
        self.master_addr_l = master_addr_l
        self.master_addr_f = master_addr_f
        self.etcd_l = etcd_l
        self.etcd_f = etcd_f
        self.data_source_l = data_source_l
        self.data_source_f = data_source_f
        self.master_l = master_l
        self.master_f = master_f
        self.data_source_name = data_source_name,
        self.etcd_name = etcd_name
        self.etcd_addrs = etcd_addrs
        self.etcd_base_dir_l = etcd_base_dir_l
        self.etcd_base_dir_f = etcd_base_dir_f
        self.raw_data_controller_l = raw_data_controller.RawDataController(
                    self.data_source_l, self.master_client_l
                )
        self.raw_data_controller_f = raw_data_controller.RawDataController(
                    self.data_source_f, self.master_client_f
                )
        if gfile.Exists(data_source_l.data_block_dir):
            gfile.DeleteRecursively(data_source_l.data_block_dir)
        if gfile.Exists(data_source_l.example_dumped_dir):
            gfile.DeleteRecursively(data_source_l.example_dumped_dir)
        if gfile.Exists(data_source_l.raw_data_dir):
            gfile.DeleteRecursively(data_source_l.raw_data_dir)
        if gfile.Exists(data_source_f.data_block_dir):
            gfile.DeleteRecursively(data_source_f.data_block_dir)
        if gfile.Exists(data_source_f.example_dumped_dir):
            gfile.DeleteRecursively(data_source_f.example_dumped_dir)
        if gfile.Exists(data_source_f.raw_data_dir):
            gfile.DeleteRecursively(data_source_f.raw_data_dir)

        self.worker_options = dj_pb.DataJoinWorkerOptions(
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
                )
            )

        self.total_index = 1 << 13

    def generate_raw_data(self, etcd, rdc, data_source, partition_id,
                          block_size, shuffle_win_size, feat_key_fmt, feat_val_fmt):
        dbm = data_block_manager.DataBlockManager(data_source, partition_id)
        raw_data_dir = os.path.join(data_source.raw_data_dir,
                                    common.partition_repr(partition_id))
        if gfile.Exists(raw_data_dir):
            gfile.DeleteRecursively(raw_data_dir)
        gfile.MakeDirs(raw_data_dir)
        useless_index = 0
        new_raw_data_fnames = []
        for block_index in range(self.total_index // block_size):
            builder = data_block_manager.DataBlockBuilder(
                    data_source.raw_data_dir,
                    data_source.data_source_meta.name,
                    partition_id, block_index, None
                )
            cands = list(range(block_index * block_size, (block_index + 1) * block_size))
            start_index = cands[0]
            for i in range(len(cands)):
                if random.randint(1, 4) > 2:
                    continue
                a = random.randint(i - shuffle_win_size, i + shuffle_win_size)
                b = random.randint(i - shuffle_win_size, i + shuffle_win_size)
                if a < 0:
                    a = 0
                if a >= len(cands):
                    a = len(cands) - 1
                if b < 0:
                    b = 0
                if b >= len(cands):
                    b = len(cands) - 1
                if (abs(cands[a]-i-start_index) <= shuffle_win_size and
                        abs(cands[b]-i-start_index) <= shuffle_win_size):
                    cands[a], cands[b] = cands[b], cands[a]
            for example_idx in cands:
                feat = {}
                example_id = '{}'.format(example_idx).encode()
                feat['example_id'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[example_id]))
                event_time = 150000000 + example_idx
                feat['event_time'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[event_time]))
                feat[feat_key_fmt.format(example_idx)] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(
                            value=[feat_val_fmt.format(example_idx).encode()]))
                example = tf.train.Example(features=tf.train.Features(feature=feat))
                builder.append(example.SerializeToString(), example_id,
                               event_time, useless_index, useless_index)
                useless_index += 1
            meta = builder.finish_data_block()
            fname = common.encode_data_block_fname(
                        data_source.data_source_meta.name,
                        meta
                    )
            new_raw_data_fnames.append(os.path.join(raw_data_dir, fname))
        fpaths = [os.path.join(raw_data_dir, f)
                    for f in gfile.ListDirectory(raw_data_dir)
                    if not gfile.IsDirectory(os.path.join(raw_data_dir, f))]
        for fpath in fpaths:
            if fpath.endswith(common.DataBlockMetaSuffix):
                gfile.Remove(fpath)
        rdc.add_raw_data(partition_id, new_raw_data_fnames, False)

    def test_all_assembly(self):
        for i in range(self.data_source_l.data_source_meta.partition_num):
            self.generate_raw_data(
                    self.etcd_l, self.raw_data_controller_l, self.data_source_l,
                    i, 2048, 64, 'leader_key_partition_{}'.format(i) + ':{}',
                    'leader_value_partition_{}'.format(i) + ':{}'
                )
            self.generate_raw_data(
                    self.etcd_f, self.raw_data_controller_f, self.data_source_f,
                    i, 4096, 128, 'follower_key_partition_{}'.format(i) + ':{}',
                    'follower_value_partition_{}'.format(i) + ':{}'
                )

        worker_addr_l = 'localhost:4161'
        worker_addr_f = 'localhost:4162'

        worker_l = data_join_worker.DataJoinWorkerService(
                int(worker_addr_l.split(':')[1]),
                worker_addr_f, self.master_addr_l, 0,
                self.etcd_name, self.etcd_base_dir_l,
                self.etcd_addrs, self.worker_options
            )

        worker_f = data_join_worker.DataJoinWorkerService(
                int(worker_addr_f.split(':')[1]),
                worker_addr_l, self.master_addr_f, 0,
                self.etcd_name, self.etcd_base_dir_f,
                self.etcd_addrs, self.worker_options
            )

        worker_l.start()
        worker_f.start()

        for i in range(self.data_source_f.data_source_meta.partition_num):
            rdmreq = dj_pb.RawDataRequest(
                    data_source_meta=self.data_source_l.data_source_meta,
                    partition_id=i,
                    finish_raw_data=empty_pb2.Empty()
                )
            rsp = self.master_client_l.FinishRawData(rdmreq)
            self.assertEqual(rsp.code, 0)
            rsp = self.master_client_f.FinishRawData(rdmreq)
            self.assertEqual(rsp.code, 0)

        while True:
            req_l = dj_pb.DataSourceRequest(
                    data_source_meta=self.data_source_l.data_source_meta
                )
            req_f = dj_pb.DataSourceRequest(
                    data_source_meta=self.data_source_f.data_source_meta
                )
            dss_l = self.master_client_l.GetDataSourceStatus(req_l)
            dss_f = self.master_client_f.GetDataSourceStatus(req_f)
            self.assertEqual(dss_l.role, common_pb.FLRole.Leader)
            self.assertEqual(dss_f.role, common_pb.FLRole.Follower)
            if dss_l.state == common_pb.DataSourceState.Finished and \
                    dss_f.state == common_pb.DataSourceState.Finished:
                break
            else:
                time.sleep(2)

        worker_l.stop()
        worker_f.stop()
        self.master_l.stop()
        self.master_f.stop()

    def tearDown(self):
        if gfile.Exists(self.data_source_l.data_block_dir):
            gfile.DeleteRecursively(self.data_source_l.data_block_dir)
        if gfile.Exists(self.data_source_l.example_dumped_dir):
            gfile.DeleteRecursively(self.data_source_l.example_dumped_dir)
        if gfile.Exists(self.data_source_l.raw_data_dir):
            gfile.DeleteRecursively(self.data_source_l.raw_data_dir)
        if gfile.Exists(self.data_source_f.data_block_dir):
            gfile.DeleteRecursively(self.data_source_f.data_block_dir)
        if gfile.Exists(self.data_source_f.example_dumped_dir):
            gfile.DeleteRecursively(self.data_source_f.example_dumped_dir)
        if gfile.Exists(self.data_source_f.raw_data_dir):
            gfile.DeleteRecursively(self.data_source_f.raw_data_dir)
        self.etcd_f.delete_prefix(self.etcd_base_dir_f)
        self.etcd_l.delete_prefix(self.etcd_base_dir_l)

if __name__ == '__main__':
        unittest.main()

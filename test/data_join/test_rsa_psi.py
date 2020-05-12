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
from os import listdir, path
from os.path import isfile, join
import time
import random
import logging
import csv
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from cityhash import CityHash32 # pylint: disable=no-name-in-module

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
from fedlearner.data_join.rsa_psi import \
        rsa_key_generator, rsa_psi_signer, rsa_psi_preprocessor
from fedlearner.data_join import (
    data_join_master, data_join_worker,
    raw_data_controller, common, csv_dict_writer
)

class RsaPsi(unittest.TestCase):
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
        self._data_source_l.raw_data_sub_dir= "./raw_data_sub_dir_l"
        self._data_source_f = common_pb.DataSource()
        self._data_source_f.role = common_pb.FLRole.Follower
        self._data_source_f.state = common_pb.DataSourceState.Init
        self._data_source_f.data_block_dir = "./data_block_f"
        self._data_source_f.raw_data_dir = "./raw_data_f"
        self._data_source_f.example_dumped_dir = "./example_dumped_f"
        self._data_source_f.raw_data_sub_dir= "./raw_data_sub_dir_f"
        data_source_meta = common_pb.DataSourceMeta()
        data_source_meta.name = self._data_source_name
        data_source_meta.partition_num = 4
        data_source_meta.start_time = 0
        data_source_meta.end_time = 100000000
        self._data_source_l.data_source_meta.MergeFrom(data_source_meta)
        self._data_source_f.data_source_meta.MergeFrom(data_source_meta)
        common.commit_data_source(self._etcd_l, self._data_source_l)
        common.commit_data_source(self._etcd_f, self._data_source_f)

    def _generate_input_csv(self, cands, base_dir):
        if not gfile.Exists(base_dir):
            gfile.MakeDirs(base_dir)
        fpaths = []
        random.shuffle(cands)
        csv_writers = []
        partition_num = self._data_source_l.data_source_meta.partition_num
        for partition_id in range(partition_num):
            fpath = os.path.join(base_dir, str(partition_id)+'.rd')
            fpaths.append(fpath)
            csv_writers.append(csv_dict_writer.CsvDictWriter(fpath, ['raw_id']))
        for item in cands:
            partition_id = CityHash32(item) % partition_num
            csv_writers[partition_id].append_raw({'raw_id': item})
        for csv_writer in csv_writers:
            csv_writer.close()
        return fpaths

    def _setUpRsaPsiConf(self):
        self._input_dir_l = './rsa_psi_raw_input_l'
        self._input_dir_f = './rsa_psi_raw_input_f'
        self._pre_processor_ouput_dir_l = './pre_processor_output_dir_l'
        self._pre_processor_ouput_dir_f = './pre_processor_output_dir_f'
        key_dir = path.join(path.dirname(path.abspath(__file__)),
                            '../rsa_key')
        self._rsa_public_key_path = path.join(key_dir, 'rsa_psi.pub')
        self._rsa_private_key_path = path.join(key_dir, 'rsa_psi')
        self._raw_data_pub_dir_l = self._data_source_l.raw_data_sub_dir
        self._raw_data_pub_dir_f = self._data_source_f.raw_data_sub_dir

    def _gen_psi_input_raw_data(self):
        self._intersection_ids = set(['{:09}'.format(i) for i in range(0, 1 << 16)
                                      if i % 3 == 0])
        self._rsa_raw_id_l = set(['{:09}'.format(i) for i in range(0, 1 << 16)
                                      if i % 2 == 0]) | self._intersection_ids
        self._rsa_raw_id_f = set(['{:09}'.format(i) for i in range(0, 1 << 16)
                                      if i % 2 == 1]) | self._intersection_ids
        self._input_dir_l = './rsa_psi_raw_input_l'
        self._input_dir_f = './rsa_psi_raw_input_f'
        self._psi_raw_data_fpaths_l = self._generate_input_csv(
                list(self._rsa_raw_id_l), self._input_dir_l
            )
        self._psi_raw_data_fpaths_f = self._generate_input_csv(
                list(self._rsa_raw_id_f), self._input_dir_f
            )

    def _remove_existed_dir(self):
        if gfile.Exists(self._input_dir_l):
            gfile.DeleteRecursively(self._input_dir_l)
        if gfile.Exists(self._input_dir_f):
            gfile.DeleteRecursively(self._input_dir_f)
        if gfile.Exists(self._pre_processor_ouput_dir_l):
            gfile.DeleteRecursively(self._pre_processor_ouput_dir_l)
        if gfile.Exists(self._pre_processor_ouput_dir_f):
            gfile.DeleteRecursively(self._pre_processor_ouput_dir_f)
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
                    raw_data_iter='CSV_DICT',
                    compressed_type=''
                ),
                example_id_dump_options=dj_pb.ExampleIdDumpOptions(
                    example_id_dump_interval=1,
                    example_id_dump_threshold=1024
                ),
                example_joiner_options=dj_pb.ExampleJoinerOptions(
                    example_joiner='SORT_RUN_JOINER',
                    min_matching_window=64,
                    max_matching_window=256,
                    data_block_dump_interval=30,
                    data_block_dump_threshold=1000
                ),
                batch_processor_options=dj_pb.BatchProcessorOptions(
                    batch_size=1024,
                    max_flying_item=4096
                ),
                data_block_builder_options=dj_pb.DataBlockBuilderOptions(
                    data_block_builder='CSV_DICT_DATABLOCK_BUILDER'
                )
            )
        self._worker_addrs_l = ['localhost:4161', 'localhost:4162',
                                'localhost:4163', 'localhost:4164']
        self._worker_addrs_f = ['localhost:5161', 'localhost:5162',
                                'localhost:5163', 'localhost:5164']
        self._workers_l = []
        self._workers_f = []
        for rank_id in range(4):
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

    def _launch_rsa_psi_signer(self):
        self._rsa_psi_signer_addr = 'localhost:6171'
        self._rsa_psi_signer = rsa_psi_signer.RsaPsiSigner(self._rsa_private_key_path, 1)
        self._rsa_psi_signer.start(int(self._rsa_psi_signer_addr.split(':')[1]))

    def _stop_workers(self):
        for w in self._workers_f:
            w.stop()
        for w in self._workers_l:
            w.stop()

    def _stop_masters(self):
        self._master_f.stop()
        self._master_l.stop()

    def _stop_rsa_psi_signer(self):
        self._rsa_psi_signer.stop()

    def setUp(self):
        self._setUpEtcd()
        self._setUpDataSource()
        self._setUpRsaPsiConf()
        self._remove_existed_dir()
        self._gen_psi_input_raw_data()
        self._launch_masters()
        self._launch_workers()
        self._launch_rsa_psi_signer()

    def _preprocess_rsa_psi_leader(self):
        processors = []
        for partition_id in range(self._data_source_l.data_source_meta.partition_num):
            options = dj_pb.RsaPsiPreProcessorOptions(
                    role=common_pb.FLRole.Leader,
                    rsa_key_file_path=self._rsa_private_key_path,
                    input_file_paths=[self._psi_raw_data_fpaths_l[partition_id]],
                    output_file_dir=self._pre_processor_ouput_dir_l,
                    raw_data_publish_dir=self._raw_data_pub_dir_l,
                    partition_id=partition_id,
                    offload_processor_number=1,
                    batch_processor_options=dj_pb.BatchProcessorOptions(
                        batch_size=1024,
                        max_flying_item=1<<14
                    )
                )
            processor = rsa_psi_preprocessor.RsaPsiPreProcessor(
                    options, self._etcd_name, self._etcd_addrs,
                    self._etcd_base_dir_l, True
                )
            processor.start_process()
            processors.append(processor)
        for processor in processors:
            processor.wait_for_finished()

    def _preprocess_rsa_psi_follower(self):
        processors = []
        for partition_id in range(self._data_source_f.data_source_meta.partition_num):
            options = dj_pb.RsaPsiPreProcessorOptions(
                    role=common_pb.FLRole.Follower,
                    rsa_key_file_path=self._rsa_public_key_path,
                    input_file_paths=[self._psi_raw_data_fpaths_f[partition_id]],
                    output_file_dir=self._pre_processor_ouput_dir_f,
                    raw_data_publish_dir=self._raw_data_pub_dir_f,
                    partition_id=partition_id,
                    leader_rsa_psi_signer_addr=self._rsa_psi_signer_addr,
                    offload_processor_number=1,
                    batch_processor_options=dj_pb.BatchProcessorOptions(
                        batch_size=1024,
                        max_flying_item=1<<14
                    )
                )
            processor = rsa_psi_preprocessor.RsaPsiPreProcessor(
                        options, self._etcd_name, self._etcd_addrs,
                        self._etcd_base_dir_f, True
                    )
            processor.start_process()
            processors.append(processor)
        for processor in processors:
            processor.wait_for_finished()

    def test_all_pipeline(self):
        start_tm = time.time()
        self._preprocess_rsa_psi_follower()
        logging.warning("Follower Preprocess cost %d seconds", time.time()-start_tm)
        start_tm = time.time()
        self._preprocess_rsa_psi_leader()
        logging.warning("Leader Preprocess cost %f seconds", time.time()-start_tm)
        rd_ctl_l = raw_data_controller.RawDataController(self._data_source_l,
                                                         self._master_client_l)
        rd_ctl_f = raw_data_controller.RawDataController(self._data_source_f,
                                                         self._master_client_f)
        partition_num = self._data_source_l.data_source_meta.partition_num
        all_finished = False
        while not all_finished:
            time.sleep(1)
            all_finished = True
            for partition_id in range(partition_num):
                manifest = self._master_client_l.QueryRawDataManifest(
                        dj_pb.RawDataRequest(
                            data_source_meta=self._data_source_l.data_source_meta,
                            partition_id=partition_id
                        )
                    )
                if manifest.next_process_index > 0:
                    rd_ctl_l.finish_raw_data(partition_id)
                else:
                    all_finished = False
                manifest = self._master_client_f.QueryRawDataManifest(
                        dj_pb.RawDataRequest(
                            data_source_meta=self._data_source_l.data_source_meta,
                            partition_id=partition_id
                        )
                    )
                if manifest.next_process_index > 0:
                    rd_ctl_f.finish_raw_data(partition_id)
                else:
                    all_finished = False

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
        self._stop_workers()
        self._stop_masters()
        self._stop_rsa_psi_signer()
        self._remove_existed_dir()

if __name__ == '__main__':
        unittest.main()

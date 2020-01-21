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
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from google.protobuf import text_format

import grpc

from fedlearner.data_join import data_join_master
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.common.etcd_client import EtcdClient
from fedlearner.proxy.channel import make_insecure_channel, ChannelType

class DataJoinMaster(unittest.TestCase):
    def test_api(self):
        etcd_name = 'test_etcd'
        etcd_addrs = 'localhost:2379'
        etcd_base_dir_l = 'byefl_l'
        etcd_base_dir_f= 'byefl_f'
        data_source_name = 'test_data_source'
        etcd_l = EtcdClient(etcd_name, etcd_addrs, etcd_base_dir_l)
        etcd_f = EtcdClient(etcd_name, etcd_addrs, etcd_base_dir_f)
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
        data_source_meta.partition_num = 1
        data_source_meta.start_time = 0
        data_source_meta.end_time = 100000000
        data_source_meta.min_matching_window = 32
        data_source_meta.max_matching_window = 1024
        data_source_meta.data_source_type = common_pb.DataSourceType.Sequential
        data_source_meta.max_example_in_data_block = 1000
        data_source_l.data_source_meta.MergeFrom(data_source_meta)
        etcd_l.set_data(os.path.join(data_source_name, 'master'),
                        text_format.MessageToString(data_source_l))
        data_source_f.data_source_meta.MergeFrom(data_source_meta)
        etcd_f.set_data(os.path.join(data_source_name, 'master'),
                        text_format.MessageToString(data_source_f))

        master_addr_l = 'localhost:4061'
        master_addr_f = 'localhost:4062'
        master_l = data_join_master.DataJoinMasterService(
                int(master_addr_l.split(':')[1]), master_addr_f,
                data_source_name, etcd_name, etcd_base_dir_l, etcd_addrs
            )
        master_l.start()
        master_f = data_join_master.DataJoinMasterService(
                int(master_addr_f.split(':')[1]), master_addr_l,
                data_source_name, etcd_name, etcd_base_dir_f, etcd_addrs
            )
        master_f.start()
        channel_l = make_insecure_channel(master_addr_l, ChannelType.INTERNAL)
        client_l = dj_grpc.DataJoinMasterServiceStub(channel_l)
        channel_f = make_insecure_channel(master_addr_f, ChannelType.INTERNAL)
        client_f = dj_grpc.DataJoinMasterServiceStub(channel_f)

        while True:
            rsp_l = client_l.GetDataSourceState(data_source_l.data_source_meta)
            rsp_f = client_f.GetDataSourceState(data_source_f.data_source_meta)
            self.assertEqual(rsp_l.status.code, 0)
            self.assertEqual(rsp_l.role, common_pb.FLRole.Leader)
            self.assertEqual(rsp_l.data_source_type, common_pb.DataSourceType.Sequential)
            self.assertEqual(rsp_f.status.code, 0)
            self.assertEqual(rsp_f.role, common_pb.FLRole.Follower)
            self.assertEqual(rsp_f.data_source_type, common_pb.DataSourceType.Sequential)
            if (rsp_l.state == common_pb.DataSourceState.Processing and 
                    rsp_f.state == common_pb.DataSourceState.Processing):
                break
            else:
                time.sleep(2)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=0,
                join_example=dj_pb.JoinExampleRequest(
                        partition_id = -1
                    )
            )

        rdrsp = client_l.RequestJoinPartition(rdreq)
        self.assertTrue(rdrsp.status.code == 0)
        self.assertFalse(rdrsp.HasField('manifest'))
        self.assertFalse(rdrsp.HasField('finished'))

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                sync_example_id=dj_pb.SyncExampleIdRequest(
                        partition_id = -1
                    )
            )
        rdrsp = client_l.RequestJoinPartition(rdreq)
        self.assertEqual(rdrsp.status.code, 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.state, dj_pb.Syncing)
        self.assertEqual(rdrsp.manifest.allocated_rank_id, 0)
        self.assertEqual(rdrsp.manifest.partition_id, 0)

        rdrsp = client_l.RequestJoinPartition(rdreq)
        self.assertEqual(rdrsp.status.code, 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.state, dj_pb.Syncing)
        self.assertEqual(rdrsp.manifest.allocated_rank_id, 0)
        self.assertEqual(rdrsp.manifest.partition_id, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=0,
                sync_example_id=dj_pb.SyncExampleIdRequest(
                        partition_id = 0
                    )
            )
        rdrsp = client_f.RequestJoinPartition(rdreq)
        self.assertEqual(rdrsp.status.code, 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.state, dj_pb.Syncing)
        self.assertEqual(rdrsp.manifest.allocated_rank_id, 0)
        self.assertEqual(rdrsp.manifest.partition_id, 0)

        frreq = dj_pb.FinishRawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                sync_example_id=dj_pb.SyncExampleIdRequest(
                        partition_id = 0
                    )
            )
        frrsp = client_l.FinishJoinPartition(frreq)
        self.assertEqual(frrsp.code, 0)
        rdrsp = client_l.FinishJoinPartition(rdreq)
        self.assertEqual(frrsp.code, 0)

        rdreq = dj_pb.FinishRawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=0,
                sync_example_id=dj_pb.SyncExampleIdRequest(
                        partition_id = 0
                    )
            )
        frrsp = client_f.FinishJoinPartition(rdreq)
        self.assertEqual(frrsp.code, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                join_example=dj_pb.JoinExampleRequest(
                        partition_id = -1
                    )
            )
        rdrsp = client_l.RequestJoinPartition(rdreq)
        self.assertEqual(rdrsp.status.code, 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.state, dj_pb.Joining)
        self.assertEqual(rdrsp.manifest.allocated_rank_id, 0)
        self.assertEqual(rdrsp.manifest.partition_id, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=0,
                join_example=dj_pb.JoinExampleRequest(
                        partition_id = 0
                    )
            )
        rdrsp = client_f.RequestJoinPartition(rdreq)
        self.assertEqual(rdrsp.status.code, 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.state, dj_pb.Joining)
        self.assertEqual(rdrsp.manifest.allocated_rank_id, 0)
        self.assertEqual(rdrsp.manifest.partition_id, 0)

        frreq = dj_pb.FinishRawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                join_example=dj_pb.JoinExampleRequest(
                        partition_id = 0
                    )
            )
        frrsp = client_l.FinishJoinPartition(rdreq)
        self.assertEqual(frrsp.code, 0)

        frrsp = client_l.FinishJoinPartition(rdreq)
        self.assertEqual(frrsp.code, 0)

        frreq = dj_pb.FinishRawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=0,
                join_example=dj_pb.JoinExampleRequest(
                        partition_id = 0
                    )
            )
        frrsp = client_f.FinishJoinPartition(rdreq)
        self.assertEqual(frrsp.code, 0)

        while True:
            rsp_l = client_l.GetDataSourceState(data_source_l.data_source_meta)
            rsp_f = client_f.GetDataSourceState(data_source_l.data_source_meta)
            self.assertEqual(rsp_l.status.code, 0)
            self.assertEqual(rsp_l.role, common_pb.FLRole.Leader)
            self.assertEqual(rsp_l.data_source_type, common_pb.DataSourceType.Sequential)
            self.assertEqual(rsp_f.status.code, 0)
            self.assertEqual(rsp_f.role, common_pb.FLRole.Follower)
            self.assertEqual(rsp_f.data_source_type, common_pb.DataSourceType.Sequential)
            if (rsp_l.state == common_pb.DataSourceState.Finished and 
                    rsp_f.state == common_pb.DataSourceState.Finished):
                break
            else:
                time.sleep(2)

        master_l.stop()
        master_f.stop()

if __name__ == '__main__':
        unittest.main()

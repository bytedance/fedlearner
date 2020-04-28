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

import grpc
from google.protobuf import text_format, empty_pb2, timestamp_pb2

from fedlearner.data_join import data_join_master
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.common.etcd_client import EtcdClient
from fedlearner.proxy.channel import make_insecure_channel, ChannelType

class DataJoinMaster(unittest.TestCase):
    def test_api(self):
        logging.getLogger().setLevel(logging.DEBUG)
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
        data_source_meta.partition_num = 1
        data_source_meta.start_time = 0
        data_source_meta.end_time = 100000000
        data_source_l.data_source_meta.MergeFrom(data_source_meta)
        etcd_l.set_data(os.path.join(data_source_name, 'master'),
                        text_format.MessageToString(data_source_l))
        data_source_f.data_source_meta.MergeFrom(data_source_meta)
        etcd_f.set_data(os.path.join(data_source_name, 'master'),
                        text_format.MessageToString(data_source_f))

        master_addr_l = 'localhost:4061'
        master_addr_f = 'localhost:4062'
        options = dj_pb.DataJoinMasterOptions(use_mock_etcd=True)
        master_l = data_join_master.DataJoinMasterService(
                int(master_addr_l.split(':')[1]),
                master_addr_f, data_source_name, etcd_name,
                etcd_base_dir_l, etcd_addrs, options
            )
        master_l.start()
        master_f = data_join_master.DataJoinMasterService(
                int(master_addr_f.split(':')[1]),
                master_addr_l, data_source_name, etcd_name,
                etcd_base_dir_f, etcd_addrs, options
            )
        master_f.start()
        channel_l = make_insecure_channel(master_addr_l, ChannelType.INTERNAL)
        client_l = dj_grpc.DataJoinMasterServiceStub(channel_l)
        channel_f = make_insecure_channel(master_addr_f, ChannelType.INTERNAL)
        client_f = dj_grpc.DataJoinMasterServiceStub(channel_f)

        while True:
            req_l = dj_pb.DataSourceRequest(
                    data_source_meta=data_source_l.data_source_meta
                )
            req_f = dj_pb.DataSourceRequest(
                    data_source_meta=data_source_f.data_source_meta
                )
            dss_l = client_l.GetDataSourceStatus(req_l)
            dss_f = client_f.GetDataSourceStatus(req_f)
            self.assertEqual(dss_l.role, common_pb.FLRole.Leader)
            self.assertEqual(dss_f.role, common_pb.FLRole.Follower)
            if dss_l.state == common_pb.DataSourceState.Processing and \
                    dss_f.state == common_pb.DataSourceState.Processing:
                break
            else:
                time.sleep(2)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=0,
                partition_id=-1,
                join_example=empty_pb2.Empty()
            )

        rdrsp = client_f.RequestJoinPartition(rdreq)
        self.assertTrue(rdrsp.status.code == 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.join_example_rep.rank_id, 0)
        self.assertEqual(rdrsp.manifest.join_example_rep.state,
                         dj_pb.JoinExampleState.Joining)
        self.assertEqual(rdrsp.manifest.partition_id, 0)

        #check idempotent
        rdrsp = client_f.RequestJoinPartition(rdreq)
        self.assertTrue(rdrsp.status.code == 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.join_example_rep.rank_id, 0)
        self.assertEqual(rdrsp.manifest.join_example_rep.state,
                         dj_pb.JoinExampleState.Joining)
        self.assertEqual(rdrsp.manifest.partition_id, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
                join_example=empty_pb2.Empty()
            )
        rdrsp = client_l.RequestJoinPartition(rdreq)
        self.assertTrue(rdrsp.status.code == 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.join_example_rep.rank_id, 0)
        self.assertEqual(rdrsp.manifest.join_example_rep.state,
                         dj_pb.JoinExampleState.Joining)
        self.assertEqual(rdrsp.manifest.partition_id, 0)
        #check idempotent
        rdrsp = client_l.RequestJoinPartition(rdreq)
        self.assertTrue(rdrsp.status.code == 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.join_example_rep.rank_id, 0)
        self.assertEqual(rdrsp.manifest.join_example_rep.state,
                         dj_pb.JoinExampleState.Joining)
        self.assertEqual(rdrsp.manifest.partition_id, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=1,
                partition_id=-1,
                sync_example_id=empty_pb2.Empty()
            )
        rdrsp = client_l.RequestJoinPartition(rdreq)
        self.assertEqual(rdrsp.status.code, 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.sync_example_id_rep.rank_id, 1)
        self.assertEqual(rdrsp.manifest.sync_example_id_rep.state,
                         dj_pb.SyncExampleIdState.Syncing)
        self.assertEqual(rdrsp.manifest.partition_id, 0)
        #check idempotent
        rdrsp = client_l.RequestJoinPartition(rdreq)
        self.assertEqual(rdrsp.status.code, 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.sync_example_id_rep.rank_id, 1)
        self.assertEqual(rdrsp.manifest.sync_example_id_rep.state,
                         dj_pb.SyncExampleIdState.Syncing)
        self.assertEqual(rdrsp.manifest.partition_id, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=1,
                partition_id = 0,
                sync_example_id=empty_pb2.Empty()
            )
        rdrsp = client_f.RequestJoinPartition(rdreq)
        self.assertEqual(rdrsp.status.code, 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.sync_example_id_rep.rank_id, 1)
        self.assertEqual(rdrsp.manifest.sync_example_id_rep.state,
                         dj_pb.SyncExampleIdState.Syncing)
        self.assertEqual(rdrsp.manifest.partition_id, 0)
        #check idempotent
        rdrsp = client_f.RequestJoinPartition(rdreq)
        self.assertEqual(rdrsp.status.code, 0)
        self.assertTrue(rdrsp.HasField('manifest'))
        self.assertEqual(rdrsp.manifest.sync_example_id_rep.rank_id, 1)
        self.assertEqual(rdrsp.manifest.sync_example_id_rep.state,
                         dj_pb.SyncExampleIdState.Syncing)
        self.assertEqual(rdrsp.manifest.partition_id, 0)

        rdreq1 = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=1,
                partition_id=0,
                sync_example_id=empty_pb2.Empty()
            )

        try:
            rsp = client_l.FinishJoinPartition(rdreq1)
        except Exception as e:
            self.assertTrue(True)
        else:
            self.assertTrue(False)

        rdreq2 = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
                join_example=empty_pb2.Empty()
            )
        try:
            rsp = client_l.FinishJoinPartition(rdreq2)
        except Exception as e:
            self.assertTrue(True)
        else:
            self.assertTrue(False)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
            )
        manifest_l = client_l.QueryRawDataManifest(rdreq)
        self.assertTrue(manifest_l is not None)
        self.assertFalse(manifest_l.finished)
        self.assertEqual(manifest_l.next_process_index, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
            )
        rsp = client_l.GetRawDataLatestTimeStamp(rdreq)
        self.assertEqual(rsp.status.code, 0)
        self.assertTrue(rsp.HasField('timestamp'))
        self.assertEqual(rsp.timestamp.seconds, 0)
        self.assertEqual(rsp.timestamp.nanos, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
                added_raw_data_metas=dj_pb.AddedRawDataMetas(
                        dedup=False,
                        raw_data_metas=[dj_pb.RawDataMeta(file_path='a',
                                        timestamp=timestamp_pb2.Timestamp(seconds=3))]
                    )
            )
        rsp = client_l.AddRawData(rdreq)
        self.assertEqual(rsp.code, 0)
        manifest_l = client_l.QueryRawDataManifest(rdreq)
        self.assertTrue(manifest_l is not None)
        self.assertFalse(manifest_l.finished)
        self.assertEqual(manifest_l.next_process_index, 1)
        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
            )
        rsp = client_l.GetRawDataLatestTimeStamp(rdreq)
        self.assertEqual(rsp.status.code, 0)
        self.assertTrue(rsp.HasField('timestamp'))
        self.assertEqual(rsp.timestamp.seconds, 3)
        self.assertEqual(rsp.timestamp.nanos, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
                added_raw_data_metas=dj_pb.AddedRawDataMetas(
                        dedup=False,
                        raw_data_metas=[dj_pb.RawDataMeta(file_path='b',
                                        timestamp=timestamp_pb2.Timestamp(seconds=5))]
                    )
            )
        rsp = client_l.AddRawData(rdreq)
        self.assertEqual(rsp.code, 0)
        manifest_l = client_l.QueryRawDataManifest(rdreq)
        self.assertTrue(manifest_l is not None)
        self.assertFalse(manifest_l.finished)
        self.assertEqual(manifest_l.next_process_index, 2)
        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
            )
        rsp = client_l.GetRawDataLatestTimeStamp(rdreq)
        self.assertEqual(rsp.status.code, 0)
        self.assertTrue(rsp.HasField('timestamp'))
        self.assertEqual(rsp.timestamp.seconds, 5)
        self.assertEqual(rsp.timestamp.nanos, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
                added_raw_data_metas=dj_pb.AddedRawDataMetas(
                        dedup=True,
                        raw_data_metas=[dj_pb.RawDataMeta(file_path='b',
                                        timestamp=timestamp_pb2.Timestamp(seconds=5)),
                                        dj_pb.RawDataMeta(file_path='a',
                                        timestamp=timestamp_pb2.Timestamp(seconds=3))]
                    )
            )
        rsp = client_l.AddRawData(rdreq)
        self.assertEqual(rsp.code, 0)
        manifest_l = client_l.QueryRawDataManifest(rdreq)
        self.assertTrue(manifest_l is not None)
        self.assertFalse(manifest_l.finished)
        self.assertEqual(manifest_l.next_process_index, 2)
        rsp = client_l.GetRawDataLatestTimeStamp(rdreq)
        self.assertEqual(rsp.status.code, 0)
        self.assertTrue(rsp.HasField('timestamp'))
        self.assertEqual(rsp.timestamp.seconds, 5)
        self.assertEqual(rsp.timestamp.nanos, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=0,
                partition_id=0,
            )
        manifest_f = client_f.QueryRawDataManifest(rdreq)
        self.assertTrue(manifest_f is not None)
        self.assertFalse(manifest_f.finished)
        self.assertEqual(manifest_f.next_process_index, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
            )
        rsp = client_f.GetRawDataLatestTimeStamp(rdreq)
        self.assertEqual(rsp.status.code, 0)
        self.assertTrue(rsp.HasField('timestamp'))
        self.assertEqual(rsp.timestamp.seconds, 0)
        self.assertEqual(rsp.timestamp.nanos, 0)
        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=0,
                partition_id=0,
                added_raw_data_metas=dj_pb.AddedRawDataMetas(
                        dedup=False,
                        raw_data_metas=[dj_pb.RawDataMeta(file_path='a',
                                        timestamp=timestamp_pb2.Timestamp(seconds=1))]
                    )
            )
        rsp = client_f.AddRawData(rdreq)
        self.assertEqual(rsp.code, 0)
        manifest_f = client_f.QueryRawDataManifest(rdreq)
        self.assertTrue(manifest_f is not None)
        self.assertFalse(manifest_f.finished)
        self.assertEqual(manifest_f.next_process_index, 1)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
            )
        rsp = client_f.GetRawDataLatestTimeStamp(rdreq)
        self.assertEqual(rsp.status.code, 0)
        self.assertTrue(rsp.HasField('timestamp'))
        self.assertEqual(rsp.timestamp.seconds, 1)
        self.assertEqual(rsp.timestamp.nanos, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=0,
                partition_id=0,
                added_raw_data_metas=dj_pb.AddedRawDataMetas(
                        dedup=False,
                        raw_data_metas=[dj_pb.RawDataMeta(file_path='b',
                                        timestamp=timestamp_pb2.Timestamp(seconds=2))]
                    )
            )
        rsp = client_f.AddRawData(rdreq)
        self.assertEqual(rsp.code, 0)
        manifest_f = client_f.QueryRawDataManifest(rdreq)
        self.assertTrue(manifest_f is not None)
        self.assertFalse(manifest_f.finished)
        self.assertEqual(manifest_f.next_process_index, 2)
        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
            )
        rsp = client_f.GetRawDataLatestTimeStamp(rdreq)
        self.assertEqual(rsp.status.code, 0)
        self.assertTrue(rsp.HasField('timestamp'))
        self.assertEqual(rsp.timestamp.seconds, 2)
        self.assertEqual(rsp.timestamp.nanos, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=0,
                partition_id=0,
                added_raw_data_metas=dj_pb.AddedRawDataMetas(
                        dedup=True,
                        raw_data_metas=[dj_pb.RawDataMeta(file_path='a',
                                        timestamp=timestamp_pb2.Timestamp(seconds=1)),
                                        dj_pb.RawDataMeta(file_path='b',
                                        timestamp=timestamp_pb2.Timestamp(seconds=2))]
                    )
            )
        rsp = client_f.AddRawData(rdreq)
        self.assertEqual(rsp.code, 0)
        manifest_f = client_f.QueryRawDataManifest(rdreq)
        self.assertTrue(manifest_f is not None)
        self.assertFalse(manifest_f.finished)
        self.assertEqual(manifest_f.next_process_index, 2)
        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
            )
        rsp = client_f.GetRawDataLatestTimeStamp(rdreq)
        self.assertEqual(rsp.status.code, 0)
        self.assertTrue(rsp.HasField('timestamp'))
        self.assertEqual(rsp.timestamp.seconds, 2)
        self.assertEqual(rsp.timestamp.nanos, 0)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
                finish_raw_data=empty_pb2.Empty()
            )
        rsp = client_l.FinishRawData(rdreq)
        self.assertEqual(rsp.code, 0)
        #check idempotent
        rsp = client_l.FinishRawData(rdreq)
        self.assertEqual(rsp.code, 0)

        manifest_l = client_l.QueryRawDataManifest(rdreq)
        self.assertTrue(manifest_l is not None)
        self.assertTrue(manifest_l.finished)
        self.assertEqual(manifest_l.next_process_index, 2)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_l.data_source_meta,
                rank_id=0,
                partition_id=0,
                added_raw_data_metas=dj_pb.AddedRawDataMetas(
                        dedup=False,
                        raw_data_metas=[dj_pb.RawDataMeta(file_path='x',
                                        timestamp=timestamp_pb2.Timestamp(seconds=4))]
                    )
            )
        try:
            rsp = client_l.AddRawData(rdreq)
        except Exception as e:
            self.assertTrue(True)
        else:
            self.assertTrue(False)

        try:
            rsp = client_f.FinishJoinPartition(rdreq2)
        except Exception as e:
            self.assertTrue(True)
        else:
            self.assertTrue(False)

        rsp = client_l.FinishJoinPartition(rdreq1)
        self.assertEqual(rsp.code, 0)
        #check idempotent
        rsp = client_l.FinishJoinPartition(rdreq1)
        self.assertEqual(rsp.code, 0)

        rsp = client_f.FinishJoinPartition(rdreq1)
        self.assertEqual(rsp.code, 0)
        #check idempotent
        rsp = client_f.FinishJoinPartition(rdreq1)
        self.assertEqual(rsp.code, 0)

        try:
            rsp = client_f.FinishJoinPartition(rdreq2)
        except Exception as e:
            self.assertTrue(True)
        else:
            self.assertTrue(False)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=0,
                partition_id=0,
                finish_raw_data=empty_pb2.Empty()
            )
        rsp = client_f.FinishRawData(rdreq)
        self.assertEqual(rsp.code, 0)
        #check idempotent
        rsp = client_f.FinishRawData(rdreq)
        self.assertEqual(rsp.code, 0)

        manifest_f = client_f.QueryRawDataManifest(rdreq)
        self.assertTrue(manifest_f is not None)
        self.assertTrue(manifest_f.finished)
        self.assertEqual(manifest_f.next_process_index, 2)

        rdreq = dj_pb.RawDataRequest(
                data_source_meta=data_source_f.data_source_meta,
                rank_id=0,
                partition_id=0,
                added_raw_data_metas=dj_pb.AddedRawDataMetas(
                        dedup=True,
                        raw_data_metas=[dj_pb.RawDataMeta(file_path='x',
                                        timestamp=timestamp_pb2.Timestamp(seconds=3))]
                    )
            )
        try:
            rsp = client_f.AddRawData(rdreq)
        except Exception as e:
            self.assertTrue(True)
        else:
            self.assertTrue(False)

        rsp = client_f.FinishJoinPartition(rdreq2)
        self.assertEqual(rsp.code, 0)
        #check idempotent
        rsp = client_f.FinishJoinPartition(rdreq2)
        self.assertEqual(rsp.code, 0)

        rsp = client_l.FinishJoinPartition(rdreq2)
        self.assertEqual(rsp.code, 0)
        #check idempotent
        rsp = client_l.FinishJoinPartition(rdreq2)
        self.assertEqual(rsp.code, 0)

        while True:
            req_l = dj_pb.DataSourceRequest(
                    data_source_meta=data_source_l.data_source_meta
                )
            req_f = dj_pb.DataSourceRequest(
                    data_source_meta=data_source_f.data_source_meta
                )
            dss_l = client_l.GetDataSourceStatus(req_l)
            dss_f = client_f.GetDataSourceStatus(req_f)
            self.assertEqual(dss_l.role, common_pb.FLRole.Leader)
            self.assertEqual(dss_f.role, common_pb.FLRole.Follower)
            if dss_l.state == common_pb.DataSourceState.Finished and \
                    dss_f.state == common_pb.DataSourceState.Finished:
                break
            else:
                time.sleep(2)

        master_l.stop()
        master_f.stop()

if __name__ == '__main__':
        unittest.main()

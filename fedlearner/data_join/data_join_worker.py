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

import argparse
import time
import logging
import zlib
from concurrent import futures

import grpc
from google.protobuf import empty_pb2

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common.etcd_client import EtcdClient
from fedlearner.proxy.channel import make_insecure_channel, ChannelType

from fedlearner.data_join import (
    example_id_sync_leader, example_id_sync_follower,
    example_join_leader, example_join_follower
)

class DataJoinWorker(dj_grpc.DataJoinWorkerServiceServicer):
    def __init__(self, peer_client, master_client,
                 rank_id, etcd, data_source, options):
        super(DataJoinWorker, self).__init__()
        self._peer_client = peer_client
        self._master_client = master_client
        self._etcd = etcd
        self._rank_id = rank_id
        self._data_source = data_source
        self._transmit_leader = None
        self._transmit_follower = None
        self._init_transmit_roles(options)

    def start(self):
        self._transmit_leader.start_routine_workers()
        self._transmit_follower.start_dump_worker()

    def stop(self):
        self._transmit_leader.stop_routine_workers()
        self._transmit_follower.stop_dump_worker()

    def StartPartition(self, request, context):
        response = dj_pb.StartPartitionResponse()
        partition_id = request.partition_id
        check_status = self._check_request(request.data_source_meta,
                                           request.rank_id,
                                           partition_id)
        if check_status.code != 0:
            response.status.MergeFrom(check_status)
            return response
        response.finished = self._is_partition_finished(partition_id)
        if not response.finished:
            transmit_follower = self._transmit_follower
            processing_partition_id = \
                    transmit_follower.get_processing_partition_id()
            if processing_partition_id is None:
                rsp = self._trigger_allocate_partition(partition_id)
                if rsp.status.code == 0 and not rsp.HasField('manifest'):
                    response.status.code = -4
                    response.status.error_message = "no manifest response"
                response.status.MergeFrom(rsp.status)
            elif partition_id != processing_partition_id:
                response.status.code = -5
                response.status.error_message = \
                        "partition %d is processing" % processing_partition_id
            if response.status.code == 0:
                response.next_index = \
                        transmit_follower.start_sync_partition(partition_id)
        return response

    def SyncPartition(self, request, context):
        partition_id = request.partition_id
        response = self._check_request(request.data_source_meta,
                                       request.rank_id,
                                       partition_id)
        if response.code == 0:
            content_bytes = request.content_bytes
            if request.compressed:
                content_bytes = zlib.decompress(content_bytes)
            sync_content = dj_pb.SyncContent()
            sync_content.ParseFromString(content_bytes)
            filled, _ = self._transmit_follower.add_synced_item(sync_content)
            if not filled:
                response.code = -4
                response.error_message = "item is not needed"
        return response

    def FinishPartition(self, request, context):
        response = dj_pb.FinishPartitionResponse()
        partition_id = request.partition_id
        check_status = self._check_request(request.data_source_meta,
                                           request.rank_id,
                                           partition_id)
        if check_status.code != 0:
            response.status.MergeFrom(check_status)
            return response
        if self._transmit_follower.get_processing_partition_id() == \
                partition_id:
            response.finished = \
                    self._transmit_follower.finish_sync_partition(
                            partition_id
                        )
        else:
            response.finished = \
                    self._is_partition_finished(partition_id)
        if response.finished:
            status = self._mark_manifest_finished(partition_id)
            if status.code == 0:
                self._transmit_follower.reset_partition(partition_id)
            response.status.MergeFrom(status)
        return response

    def _decode_sync_content(self, content_bytes, compressed):
        if compressed:
            content_bytes = zlib.decompress(content_bytes)
        sync_content = dj_pb.SyncContent()
        sync_content.ParseFromString(content_bytes)
        return sync_content

    def _init_transmit_roles(self, options):
        if self._data_source.role == common_pb.FLRole.Leader:
            self._transmit_leader = \
                    example_id_sync_leader.ExampleIdSyncLeader(
                            self._peer_client, self._master_client,
                            self._rank_id, self._etcd,
                            self._data_source, options.raw_data_options,
                        )
            self._transmit_follower = \
                    example_join_follower.ExampleJoinFollower(
                            self._etcd, self._data_source,
                            options.raw_data_options
                        )
        else:
            assert self._data_source.role == common_pb.FLRole.Follower, \
                "if not Leader, otherwise, must be Follower"
            self._transmit_leader = \
                    example_join_leader.ExampleJoinLeader(
                            self._peer_client, self._master_client,
                            self._rank_id, self._etcd, self._data_source,
                            options.raw_data_options,
                            options.example_joiner_options
                        )
            self._transmit_follower = \
                    example_id_sync_follower.ExampleIdSyncFollower(
                            self._etcd, self._data_source,
                            options.example_id_dump_options
                        )

    def _check_request(self, remote_meta, remote_rank_id, partition_id):
        if remote_meta != self._data_source.data_source_meta:
            return common_pb.Status(
                    code=-1, error_message="data source meta is mismatch"
                )
        if remote_rank_id != self._rank_id:
            return common_pb.Status(
                    code=-2,
                    error_message="rank_id mismatch. {}(caller) != {}(srv)"\
                                  .format(remote_rank_id, self._rank_id)
                )
        partition_num = self._data_source.data_source_meta.partition_num
        if partition_id < 0 or partition_id > partition_num:
            return common_pb.Status(
                    code=-3,
                    error_message="partition-{} is out of range[0, {})"\
                            .format(partition_id, partition_num)
                )
        return common_pb.Status(code=0)

    def _is_partition_finished(self, partition_id):
        request = dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                partition_id=partition_id
            )
        manifest = self._master_client.QueryRawDataManifest(request)
        assert manifest is not None and \
                manifest.partition_id == partition_id
        if self._data_source.role == common_pb.FLRole.Leader:
            return manifest.join_example_rep.state == \
                    dj_pb.JoinExampleState.Joined
        assert self._data_source.role == common_pb.FLRole.Follower, \
            "if not Leader, otherwise, must be Follower"
        return manifest.sync_example_id_rep.state == \
                dj_pb.SyncExampleIdState.Synced

    def _trigger_allocate_partition(self, partition_id):
        request = self._make_raw_data_request(partition_id)
        return self._master_client.RequestJoinPartition(request)

    def _mark_manifest_finished(self, partition_id):
        request = self._make_raw_data_request(partition_id)
        return self._master_client.FinishJoinPartition(request)

    def _make_raw_data_request(self, partition_id):
        if self._data_source.role == common_pb.FLRole.Leader:
            return dj_pb.RawDataRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    rank_id=self._rank_id,
                    partition_id=partition_id,
                    join_example=empty_pb2.Empty()
                )
        assert self._data_source.role == common_pb.FLRole.Follower, \
            "if not Leader, otherwise, must be Follower"
        return dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                partition_id=partition_id,
                sync_example_id=empty_pb2.Empty()
            )

class DataJoinWorkerService(object):
    def __init__(self, listen_port, peer_addr, master_addr, rank_id,
                 etcd_name, etcd_base_dir, etcd_addrs, options):
        master_channel = make_insecure_channel(
                master_addr, ChannelType.INTERNAL
            )
        master_client = dj_grpc.DataJoinMasterServiceStub(master_channel)
        etcd = EtcdClient(etcd_name, etcd_addrs,
                          etcd_base_dir, options.use_mock_etcd)
        data_source = self.sync_data_source(master_client)
        self._data_source_name = data_source.data_source_meta.name
        self._listen_port = listen_port
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        peer_channel = make_insecure_channel(peer_addr, ChannelType.REMOTE)
        peer_client = dj_grpc.DataJoinWorkerServiceStub(peer_channel)
        self._data_join_worker = DataJoinWorker(
                peer_client, master_client,
                rank_id, etcd, data_source, options
            )
        dj_grpc.add_DataJoinWorkerServiceServicer_to_server(
                    self._data_join_worker, self._server
                )
        self._role_repr = "leader" if data_source.role == \
                common_pb.FLRole.Leader else "follower"
        self._server.add_insecure_port('[::]:%d'%listen_port)
        self._server_started = False

    def sync_data_source(self, master_client):
        while True:
            try:
                return master_client.GetDataSource(empty_pb2.Empty())
            except Exception as e: # pylint: disable=broad-except
                logging.warning("Failed to get data source from master with "\
                                "exception %s. sleep 2 second and retry", e)
            time.sleep(2)

    def start(self):
        if not self._server_started:
            self._server.start()
            self._data_join_worker.start()
            self._server_started = True
            logging.info("DataJoinWorker(%s) for data_source %s "\
                         "start on port[%d]", self._role_repr,
                         self._data_source_name, self._listen_port)

    def stop(self):
        if self._server_started:
            self._data_join_worker.stop()
            self._server.stop(None)
            self._server_started = False
            logging.info("DataJoinWorker(%s) for data_source %s stopped",
                         self._role_repr, self._data_source_name)

    def run(self):
        self.start()
        self._server.wait_for_termination()
        self.stop()

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    parser = argparse.ArgumentParser(description='DataJoinWorkerService cmd.')
    parser.add_argument('peer_addr', type=str,
                        help='the addr(uuid) of peer data join worker')
    parser.add_argument('master_addr', type=str,
                        help='the addr(uuid) of local data join master')
    parser.add_argument('rank_id', type=int,
                        help='the rank id for this worker')
    parser.add_argument('--etcd_name', type=str,
                        default='test_etcd', help='the name of etcd')
    parser.add_argument('--etcd_base_dir', type=str, default='fedlearner_test',
                        help='the namespace of etcd key')
    parser.add_argument('--etcd_addrs', type=str,
                        default='localhost:4578', help='the addrs of etcd')
    parser.add_argument('--tf_eager_mode', action='store_true',
                        help='use the eager_mode for tf')
    parser.add_argument('--use_mock_etcd', action='store_true',
                        help='use to mock etcd for test')
    parser.add_argument('--listen_port', '-p', type=int, default=4132,
                        help='Listen port of data join master')
    parser.add_argument('--raw_data_iter', type=str, default='TF_RECORD',
                        help='the type for raw data file')
    parser.add_argument('--compressed_type', type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type for raw data')
    parser.add_argument('--example_joiner', type=str,
                        default='STREAM_JOINER',
                        help='the method for example joiner')
    parser.add_argument('--min_matching_window', type=int, default=1024,
                        help='the min matching window for example join. '\
                             '<=0 means window size is infinite')
    parser.add_argument('--max_matching_window', type=int, default=4096,
                        help='the max matching window for example join. '\
                             '<=0 means window size is infinite')
    parser.add_argument('--data_block_dump_interval', type=int, default=-1,
                        help='dump a data block every interval, <=0'\
                             'means no time limit for dumping data block')
    parser.add_argument('--data_block_dump_threshold', type=int, default=4096,
                        help='dump a data block if join N example, <=0'\
                             'means no size limit for dumping data block')
    parser.add_argument('--example_id_dump_interval', type=int, default=-1,
                        help='dump leader example id interval, <=0'\
                             'means no time limit for dumping example id')
    parser.add_argument('--example_id_dump_threshold', type=int, default=4096,
                        help='dump a data block if N example id, <=0'\
                             'means no size limit for dumping example id')
    args = parser.parse_args()
    if args.tf_eager_mode:
        import tensorflow
        tensorflow.compat.v1.enable_eager_execution()
    worker_options = dj_pb.DataJoinWorkerOptions(
            use_mock_etcd=args.use_mock_etcd,
            raw_data_options=dj_pb.RawDataOptions(
                    raw_data_iter=args.raw_data_iter,
                    compressed_type=args.compressed_type
                ),
            example_joiner_options=dj_pb.ExampleJoinerOptions(
                    example_joiner=args.example_joiner,
                    min_matching_window=args.min_matching_window,
                    max_matching_window=args.max_matching_window,
                    data_block_dump_interval=args.data_block_dump_interval,
                    data_block_dump_threshold=args.data_block_dump_threshold,
                ),
            example_id_dump_options=dj_pb.ExampleIdDumpOptions(
                    example_id_dump_interval=args.example_id_dump_interval,
                    example_id_dump_threshold=args.example_id_dump_threshold
                )
        )
    worker_srv = DataJoinWorkerService(args.listen_port, args.peer_addr,
                                       args.master_addr, args.rank_id,
                                       args.etcd_name, args.etcd_base_dir,
                                       args.etcd_addrs, worker_options)
    worker_srv.run()

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
from concurrent import futures

import grpc
from google.protobuf import empty_pb2

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.common.etcd_client import EtcdClient
from fedlearner.proxy.channel import make_insecure_channel, ChannelType

from fedlearner.data_join import (
    data_join_leader, data_join_follower, customized_options
)

class DataJoinWorkerService(object):
    def __init__(self, listen_port, peer_addr, master_addr, rank_id,
                 etcd_name, etcd_base_dir, etcd_addrs, options):
        master_channel = make_insecure_channel(
                master_addr, ChannelType.INTERNAL
            )
        master_client = dj_grpc.DataJoinMasterServiceStub(master_channel)
        etcd = EtcdClient(etcd_name, etcd_addrs, etcd_base_dir)
        data_source = self.sync_data_source(master_client)
        self._data_source_name = data_source.data_source_meta.name
        self._listen_port = listen_port
        self._rank_id = rank_id
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        peer_channel = make_insecure_channel(peer_addr, ChannelType.REMOTE)
        if data_source.role == common_pb.FLRole.Leader:
            self._role_repr = "leader"
            peer_client = dj_grpc.DataJoinFollowerServiceStub(peer_channel)
            self._diw = data_join_leader.DataJoinLeader(
                    peer_client, master_client, rank_id,
                    etcd, data_source, options
                )
            dj_grpc.add_DataJoinLeaderServiceServicer_to_server(
                    self._diw, self._server
                )
        else:
            assert data_source.role == common_pb.FLRole.Follower
            self._role_repr = "follower"
            peer_client = dj_grpc.DataJoinLeaderServiceStub(peer_channel)
            self._diw = data_join_follower.DataJoinFollower(
                    peer_client, master_client, rank_id,
                    etcd, data_source, options
                )
            dj_grpc.add_DataJoinFollowerServiceServicer_to_server(
                    self._diw, self._server
                )
        self._server.add_insecure_port('[::]:%d'%listen_port)
        self._server_started = False

    def sync_data_source(self, master_client):
        while True:
            try:
                return master_client.GetDataSource(empty_pb2.Empty())
            except Exception as e: # pylint: disable=broad-except
                logging.warning(
                        "Failed to get data source from master with "\
                        "exception %s. sleep 2 second and retry", e
                    )
            time.sleep(2)

    def start(self):
        if not self._server_started:
            self._server.start()
            self._diw.start()
            self._server_started = True
            logging.info(
                    "DataJoinWorker(%s) for data_source %s "\
                    "start on port[%d]", self._role_repr,
                    self._data_source_name, self._listen_port
                )

    def stop(self):
        if self._server_started:
            self._diw.stop()
            self._server.stop(None)
            self._server_started = False
            logging.info(
                    "DataJoinWorker(%s) for data_source %s "\
                    "stopped", self._role_repr, self._data_source_name
                )

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
    parser.add_argument('--etcd_base_dir', type=str, default='fedlearner',
                        help='the namespace of etcd key')
    parser.add_argument('--etcd_addrs', type=str,
                        default='localhost:4578', help='the addrs of etcd')
    parser.add_argument('--listen_port', '-p', type=int, default=4132,
                        help='Listen port of data join master')
    parser.add_argument('--raw_data_iter', type=str, default='TF_RECORD',
                        help='the type for raw data file')
    parser.add_argument('--example_joiner', type=str,
                        default='STREAM_JOINER',
                        help='the method for example joiner')
    parser.add_argument('--compressed_type', type=str,
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type for raw data')
    parser.add_argument('--tf_eager_mode', action='store_true',
                        help='use the eager_mode for tf')
    args = parser.parse_args()
    cst_options = customized_options.CustomizedOptions()
    if args.raw_data_iter is not None:
        cst_options.set_raw_data_iter(args.raw_data_iter)
    if args.example_joiner is not None:
        cst_options.set_example_joiner(args.example_joiner)
    if args.compressed_type is not None:
        cst_options.set_compressed_type(args.compressed_type)
    if args.tf_eager_mode:
        import tensorflow
        tensorflow.compat.v1.enable_eager_execution()
    worker_srv = DataJoinWorkerService(
            args.listen_port, args.peer_addr, args.master_addr,
            args.rank_id, args.etcd_name, args.etcd_base_dir,
            args.etcd_addrs, cst_options
        )
    worker_srv.run()

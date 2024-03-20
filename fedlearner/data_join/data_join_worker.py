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

import time
import logging
from concurrent import futures

import grpc
from google.protobuf import empty_pb2

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common.db_client import DBClient
from fedlearner.proxy.channel import make_insecure_channel, ChannelType

from fedlearner.data_join import (
    example_id_sync_leader, example_id_sync_follower,
    example_join_leader, example_join_follower
)

class DataJoinWorker(dj_grpc.DataJoinWorkerServiceServicer):
    def __init__(self, peer_client, master_client,
                 rank_id, kvstore, data_source, options):
        super(DataJoinWorker, self).__init__()
        self._peer_client = peer_client
        self._master_client = master_client
        self._kvstore = kvstore
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
                response.next_index, response.dumped_index = \
                        transmit_follower.start_sync_partition(partition_id)
        return response

    def SyncPartition(self, request, context):
        partition_id = request.partition_id
        response = dj_pb.SyncPartitionResponse()
        status = self._check_request(request.data_source_meta,
                                     request.rank_id,
                                     partition_id)
        response.status.MergeFrom(status)
        if response.status.code == 0:
            sync_content = request.sync_content
            filled, response.next_index, response.dumped_index = \
                    self._transmit_follower.add_synced_item(sync_content)
            if not filled:
                response.status.code = -4
                response.status.error_message = "item is not filled, expected "\
                                                "{}".format(response.next_index)
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
            response.finished, response.dumped_index = \
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

    def _init_transmit_roles(self, options):
        if self._data_source.role == common_pb.FLRole.Leader:
            self._transmit_leader = \
                    example_id_sync_leader.ExampleIdSyncLeader(
                            self._peer_client, self._master_client,
                            self._rank_id, self._kvstore,
                            self._data_source, options.raw_data_options,
                            options.batch_processor_options
                        )
            self._transmit_follower = \
                    example_join_follower.ExampleJoinFollower(
                            self._kvstore, self._data_source,
                            options.raw_data_options,
                            options.data_block_builder_options,
                        )
        else:
            assert self._data_source.role == common_pb.FLRole.Follower, \
                "if not Leader, otherwise, must be Follower"
            self._transmit_leader = \
                    example_join_leader.ExampleJoinLeader(
                            self._peer_client, self._master_client,
                            self._rank_id, self._kvstore, self._data_source,
                            options.raw_data_options,
                            options.data_block_builder_options,
                            options.example_joiner_options
                        )
            self._transmit_follower = \
                    example_id_sync_follower.ExampleIdSyncFollower(
                            self._kvstore, self._data_source,
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
                 kvstore_type, options):
        master_channel = make_insecure_channel(
                master_addr, ChannelType.INTERNAL,
                options=[('grpc.max_send_message_length', 2**31-1),
                         ('grpc.max_receive_message_length', 2**31-1)]
            )
        self._master_client = dj_grpc.DataJoinMasterServiceStub(master_channel)
        self._rank_id = rank_id
        kvstore = DBClient(kvstore_type, options.use_mock_etcd)
        data_source = self._sync_data_source()
        self._data_source_name = data_source.data_source_meta.name
        self._listen_port = listen_port
        self._server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=10),
            options=[('grpc.max_send_message_length', 2**31-1),
                     ('grpc.max_receive_message_length', 2**31-1)])

        peer_channel = make_insecure_channel(
                peer_addr, ChannelType.REMOTE,
                options=[('grpc.max_send_message_length', 2**31-1),
                         ('grpc.max_receive_message_length', 2**31-1)]
            )
        peer_client = dj_grpc.DataJoinWorkerServiceStub(peer_channel)
        self._data_join_worker = DataJoinWorker(
                peer_client, self._master_client,
                rank_id, kvstore, data_source, options
            )
        dj_grpc.add_DataJoinWorkerServiceServicer_to_server(
                    self._data_join_worker, self._server
                )
        self._role_repr = "leader" if data_source.role == \
                common_pb.FLRole.Leader else "follower"
        self._server.add_insecure_port('[::]:%d'%listen_port)
        self._server_started = False

    def _sync_data_source(self):
        while True:
            try:
                return self._master_client.GetDataSource(empty_pb2.Empty())
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

    def _wait_for_join_finished(self):
        while True:
            data_source = self._sync_data_source()
            if data_source.state > common_pb.DataSourceState.Processing:
                logging.warning("DataSource state run to %d, no task will "\
                                "be allocated. Data Join Worker-[%d] will "\
                                "exit after 60s",
                                data_source.state, self._rank_id)
                time.sleep(60)
                break
            if data_source.state == common_pb.DataSourceState.UnKnown:
                logging.error("DataSource state run to at state Unknow. Data "\
                              "Join Worker-[%d] will exit", self._rank_id)
            logging.debug("DataSource at state %d, wait 10s and recheck")
            time.sleep(10)

    def run(self):
        self.start()
        self._wait_for_join_finished()
        self.stop()

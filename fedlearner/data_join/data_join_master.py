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
import threading
import logging
import os
from concurrent import futures

import grpc
from google.protobuf import text_format, empty_pb2

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc

from fedlearner.common.etcd_client import EtcdClient
from fedlearner.proxy.channel import make_insecure_channel, ChannelType

from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.raw_data_manifest_manager import (
    RawDataManifestManager
)
from fedlearner.data_join import customized_options

class MasterFSM(object):
    INVALID_PEER_FSM_STATE = {}
    INVALID_PEER_FSM_STATE[common_pb.DataSourceState.Init] = set(
            [common_pb.DataSourceState.Failed,
             common_pb.DataSourceState.Ready,
             common_pb.DataSourceState.Finished]
        )
    INVALID_PEER_FSM_STATE[common_pb.DataSourceState.Processing] = set(
            [common_pb.DataSourceState.Failed,
             common_pb.DataSourceState.Finished]
        )
    INVALID_PEER_FSM_STATE[common_pb.DataSourceState.Ready] = set(
            [common_pb.DataSourceState.Failed,
             common_pb.DataSourceState.Init]
        )
    INVALID_PEER_FSM_STATE[common_pb.DataSourceState.Finished] = set(
            [common_pb.DataSourceState.Failed,
             common_pb.DataSourceState.Init,
             common_pb.DataSourceState.Processing]
        )

    def __init__(self, peer_client, data_source_name, etcd):
        self._lock = threading.Lock()
        self._peer_client = peer_client
        self._data_source_name = data_source_name
        self._master_etcd_key = os.path.join(data_source_name, 'master')
        self._etcd = etcd
        self._init_fsm_action()
        self._data_source = None
        self._sync_data_source()
        assert self._data_source is not None
        self._raw_data_manifest_manager = RawDataManifestManager(
                etcd, self._data_source
            )
        assert self._data_source is not None
        self._data_source_meta = self._data_source.data_source_meta
        if self._data_source.role == common_pb.FLRole.Leader:
            self._role_repr = "leader"
        else:
            self._role_repr = "follower"
        self._fsm_worker = None
        self._started = False

    def get_mainifest_manager(self):
        return self._raw_data_manifest_manager

    def get_data_source(self):
        with self._lock:
            self._sync_data_source()
            assert self._data_source is not None
            return self._data_source

    def set_failed(self):
        return self.set_state(common_pb.DataSourceState.Failed, None)

    def set_state(self, new_state, origin_state=None):
        with self._lock:
            try:
                self._sync_data_source()
                assert self._data_source is not None
                if self._data_source.state == new_state:
                    return True
                if (origin_state is None or
                        self._data_source.state == origin_state):
                    self._data_source.state = new_state
                    self._update_data_source(self._data_source)
                    return True
                logging.warning("DataSource: %s failed to set to state: "
                                "%d, origin state mismatch(%d != %d)",
                                self._data_source_name, new_state,
                                origin_state, self._data_source.state)
                return False
            except Exception as e: # pylint: disable=broad-except
                logging.warning("Faile to set state to %d with exception %s",
                                new_state, e)
                return False
            return True

    def start_fsm_worker(self):
        with self._lock:
            if not self._started:
                assert self._fsm_worker is None
                self._started = True
                self._fsm_worker = RoutineWorker(
                        '{}_fsm_worker'.format(self._data_source_name),
                        self._fsm_routine_fn,
                        self._fsm_routine_cond, 5
                    )
                self._fsm_worker.start_routine()

    def stop_fsm_worker(self):
        tmp_worker = None
        with self._lock:
            if self._fsm_worker is not None:
                tmp_worker = self._fsm_worker
                self._fsm_worker = None
        if tmp_worker is not None:
            tmp_worker.stop_routine()

    def _fsm_routine_fn(self):
        peer_info = self._get_peer_data_source_state()
        if peer_info.status.code != 0:
            logging.error("Failed to get peer state, %s",
                           peer_info.status.error_message)
            return
        with self._lock:
            self._sync_data_source()
            assert self._data_source is not None
            state = self._data_source.state
            if self._fallback_failed_state(peer_info):
                logging.warning(
                        "Self(%s) at state %d, Peer at state %d "\
                        "state invalid! abort data source %s",
                        self._role_repr, state,
                        peer_info.state, self._data_source_name
                    )
            elif state not in self._fsm_driven_handle:
                logging.error(
                        "Self(%s) at error state %d for data_source %s",
                        self._role_repr, state, self._data_source_name
                    )
            else:
                state_changed = self._fsm_driven_handle[state](peer_info)
                if state_changed:
                    self._sync_data_source()
                    assert self._data_source is not None
                    new_state = self._data_source.state
                    logging.warning(
                            "Self(%s) state changed from %d to %d",
                            self._role_repr, state, new_state
                        )

    def _fsm_routine_cond(self):
        return True

    def _sync_data_source(self):
        if self._data_source is None:
            raw_data = self._etcd.get_data(self._master_etcd_key)
            if raw_data is None:
                raise ValueError(
                        "etcd master key is None for {}".format(
                            self._data_source_name)
                    )
            self._data_source = text_format.Parse(
                    raw_data, common_pb.DataSource()
                )

    def _init_fsm_action(self):
        self._fsm_driven_handle = {
             common_pb.DataSourceState.UnKnown:
                 self._get_fsm_action('unknown'),
             common_pb.DataSourceState.Init:
                 self._get_fsm_action('init'),
             common_pb.DataSourceState.Processing:
                 self._get_fsm_action('processing'),
             common_pb.DataSourceState.Ready:
                 self._get_fsm_action('ready'),
             common_pb.DataSourceState.Finished:
                 self._get_fsm_action('finished'),
             common_pb.DataSourceState.Failed:
                 self._get_fsm_action('failed')
        }

    def _get_fsm_action(self, action):
        def _not_implement(useless):
            raise NotImplementedError('state is not NotImplemented')
        name = '_fsm_{}_action'.format(action)
        return getattr(self, name, _not_implement)

    def _fsm_init_action(self, peer_info):
        state_changed = False
        if self._data_source.role == common_pb.FLRole.Leader:
            if peer_info.state == common_pb.DataSourceState.Init:
                state_changed = True
        elif peer_info.state == common_pb.DataSourceState.Processing:
            state_changed = True
        if state_changed:
            self._data_source.state = common_pb.DataSourceState.Processing
            self._update_data_source(self._data_source)
            return True
        return False

    def _fsm_processing_action(self, peer_info):
        if self._all_partition_finished():
            state_changed = False
            if self._data_source.role == common_pb.FLRole.Leader:
                if peer_info.state == common_pb.DataSourceState.Processing:
                    state_changed = True
            elif peer_info.state == common_pb.DataSourceState.Ready:
                state_changed = True
            if state_changed:
                self._data_source.state = common_pb.DataSourceState.Ready
                self._update_data_source(self._data_source)
                return True
        return False

    def _fsm_ready_action(self, peer_info):
        state_changed = False
        if self._data_source.role == common_pb.FLRole.Leader:
            if peer_info.state == common_pb.DataSourceState.Ready:
                state_changed = True
        elif peer_info.state == common_pb.DataSourceState.Finished:
            state_changed = True
        if state_changed:
            self._data_source.state = common_pb.DataSourceState.Finished
            self._update_data_source(self._data_source)
            return True
        return False

    def _fsm_finished_action(self, peer_info):
        return False

    def _fsm_failed_action(self, peer_info):
        if peer_info.state != common_pb.DataSourceState.Failed:
            self._peer_client.AbortDataSource(self._data_source_meta)
        return False

    def _fallback_failed_state(self, peer_info):
        state = self._data_source.state
        if (state in self.INVALID_PEER_FSM_STATE and
                peer_info.state in self.INVALID_PEER_FSM_STATE[state]):
            self._data_source.state = common_pb.DataSourceState.Failed
            self._update_data_source(self._data_source)
            return True
        return False

    def _update_data_source(self, data_source):
        self._data_source = None
        try:
            self._etcd.set_data(self._master_etcd_key,
                                text_format.MessageToString(data_source))
        except Exception as e:
            logging.error("Failed to update data source: %s since "\
                          "exception: %s", self._data_source_name, e)
            raise
        self._data_source = data_source
        logging.debug("Success update to update data source: %s.",
                       self._data_source_name)

    def _get_peer_data_source_state(self):
        return self._peer_client.GetDataSourceState(self._data_source_meta)

    def _all_partition_finished(self):
        all_manifest = self._raw_data_manifest_manager.list_all_manifest()
        assert (len(all_manifest) ==
                    self._data_source.data_source_meta.partition_num)
        for manifest in all_manifest.values():
            if manifest.state != dj_pb.RawDataState.Done:
                return False
        return True

class DataJoinMaster(dj_grpc.DataJoinMasterServiceServicer):
    def __init__(self, peer_client, data_source_name,
                 etcd_name, etcd_addrs, etcd_base_dir):
        super(DataJoinMaster, self).__init__()
        self._data_source_name = data_source_name
        etcd = EtcdClient(etcd_name, etcd_addrs, etcd_base_dir,
                          customized_options.get_use_mock_etcd())
        self._fsm = MasterFSM(peer_client, data_source_name, etcd)

    def GetDataSource(self, request, context):
        return self._fsm.get_data_source()

    def GetDataSourceState(self, request, context):
        response = dj_pb.DataSourceStateResponse()
        data_source = self._fsm.get_data_source()
        if not self._validate_data_source_meta(request,
                                               data_source.data_source_meta):
            response.status.code = -2
            response.status.error_message = 'data source meta mismtach'
        else:
            response.status.code = 0
            response.role = data_source.role
            response.state = data_source.state
            response.data_source_type = (
                data_source.data_source_meta.data_source_type)
        return response

    def AbortDataSource(self, request, context):
        response = common_pb.Status()
        data_source = self._fsm.get_data_source()
        if not self._validate_data_source_meta(request,
                                               data_source.data_source_meta):
            response.code = -1
            response.error_message = 'data source meta mismtach'
        elif not self._fsm.set_failed():
            response.code = -2
            response.error_message = "failed to set failed state to fsm"
        else:
            response.code = 0
        return response

    def RequestJoinPartition(self, request, context):
        response = dj_pb.RawDataResponse()
        response.status.code = 0
        data_source = self._fsm.get_data_source()
        if not self._validate_data_source_meta(request.data_source_meta,
                                               data_source.data_source_meta):
            response.status.code = -1
            response.status.error_message = 'data source meta mismtach'
            return response
        if data_source.state != common_pb.DataSourceState.Processing:
            response.status.code = -2
            response.status.error_message = (
                "data source is not at processing state")
            return response
        rank_id = request.rank_id
        manifest = None
        finished = False
        manifest_manager = self._fsm.get_mainifest_manager()
        if request.HasField('sync_example_id'):
            partition_id = None
            if request.sync_example_id.partition_id >= 0:
                partition_id = request.sync_example_id.partition_id
            manifest, finished = manifest_manager.alloc_unallocated_partition(
                    rank_id, partition_id
                )
        elif request.HasField('join_example'):
            partition_id = None
            if request.join_example.partition_id >= 0:
                partition_id = request.join_example.partition_id
            manifest, finished = manifest_manager.alloc_synced_partition(
                    rank_id, partition_id
                )
        else:
            raise RuntimeError("unknown request type")
        if manifest is not None:
            response.manifest.MergeFrom(manifest)
        elif finished:
            response.finished.MergeFrom(empty_pb2.Empty())
        return response

    def FinishJoinPartition(self, request, context):
        response = common_pb.Status()
        response.code = 0
        data_source = self._fsm.get_data_source()
        if not self._validate_data_source_meta(request.data_source_meta,
                                               data_source.data_source_meta):
            response.code = -1
            response.error_message = 'data source meta mismtach'
            return response
        if data_source.state != common_pb.DataSourceState.Processing:
            response.code = -2
            response.error_message = "data source is not at processing state"
            return response
        rank_id = request.rank_id
        manifest_manager = self._fsm.get_mainifest_manager()
        if request.HasField('sync_example_id'):
            partition_id = request.sync_example_id.partition_id
            manifest_manager.finish_sync_partition(rank_id, partition_id)
        elif request.HasField('join_example'):
            partition_id = request.join_example.partition_id
            manifest_manager.finish_join_partition(rank_id, partition_id)
        else:
            raise RuntimeError("unknown request type")
        return response

    def QueryRawDataManifest(self, request, context):
        response = dj_pb.RawDataManifestResponse()
        response.status.code = 0
        data_source = self._fsm.get_data_source()
        if not self._validate_data_source_meta(request.data_source_meta,
                                               data_source.data_source_meta):
            response.status.code = -1
            response.status.error_message = 'data source meta mismtach'
            return response
        manifest_manager = self._fsm.get_mainifest_manager()
        manifest = manifest_manager.get_manifest(request.partition_id)
        assert manifest is not None
        response.manifest.MergeFrom(manifest)
        return response

    def start_fsm(self):
        self._fsm.start_fsm_worker()

    def stop_fsm(self):
        self._fsm.stop_fsm_worker()

    @staticmethod
    def _validate_data_source_meta(remote_meta, local_meta):
        return remote_meta == local_meta

class DataJoinMasterService(object):
    def __init__(self, listen_port, peer_addr, data_source_name,
                 etcd_name, etcd_base_dir, etcd_addrs):
        channel = make_insecure_channel(peer_addr, ChannelType.REMOTE)
        peer_client = dj_grpc.DataJoinMasterServiceStub(channel)
        self._data_source_name = data_source_name
        self._listen_port = listen_port
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        self._dim = DataJoinMaster(
                peer_client, data_source_name,
                etcd_name, etcd_addrs, etcd_base_dir
            )
        dj_grpc.add_DataJoinMasterServiceServicer_to_server(
                self._dim, self._server
            )
        self._server.add_insecure_port('[::]:%d'%listen_port)
        self._server_started = False

    def start(self):
        if not self._server_started:
            self._server.start()
            self._dim.start_fsm()
            self._server_started = True
            logging.info(
                    "DataJoinMasterService for data_source %s start "\
                    "on port[%d]", self._data_source_name, self._listen_port
                )

    def stop(self):
        if self._server_started:
            self._dim.stop_fsm()
            self._server.stop(None)
            self._server_started = False
            logging.info(
                    "DataJoinMasterService for data_source %s "\
                    "stopped ", self._data_source_name
                )

    def run(self):
        self.start()
        self._server.wait_for_termination()
        self.stop()

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser(description='DataJointMasterService cmd.')
    parser.add_argument('peer_addr', type=str,
                        help='the addr(uuid) of peer data join master')
    parser.add_argument('--etcd_name', type=str,
                        default='test_etcd', help='the name of etcd')
    parser.add_argument('--etcd_addrs', type=str,
                        default='localhost:4578', help='the addrs of etcd')
    parser.add_argument('--etcd_base_dir', type=str, default='fedlearner_test',
                        help='the namespace of etcd key')
    parser.add_argument('--listen_port', '-p', type=int, default=4032,
                        help='Listen port of data join master')
    parser.add_argument('--data_source_name', type=str,
                        default='test_data_source',
                        help='the name of data source')
    parser.add_argument('--use_mock_etcd', action='store_true',
                        help='use to mock etcd for test')
    args = parser.parse_args()
    if args.use_mock_etcd:
        customized_options.set_use_mock_etcd()
    master_srv = DataJoinMasterService(
            args.listen_port, args.peer_addr, args.data_source_name,
            args.etcd_name, args.etcd_base_dir, args.etcd_addrs
        )
    master_srv.run()

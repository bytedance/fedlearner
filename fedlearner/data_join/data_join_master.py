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

import logging
import os
import threading
import time
from concurrent import futures

import grpc
import tensorflow as tf
from google.protobuf import empty_pb2, timestamp_pb2
from elasticsearch import Elasticsearch

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.common.mysql_client import DBClient
from fedlearner.data_join.common import retrieve_data_source, commit_data_source
from fedlearner.data_join.raw_data_manifest_manager import (
    RawDataManifestManager
)
from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.proxy.channel import make_insecure_channel, ChannelType


class MasterFSM(object):
    INVALID_PEER_FSM_STATE = {  # dict of sets
        common_pb.DataSourceState.Init: {
            common_pb.DataSourceState.Failed,
            common_pb.DataSourceState.Ready,
            common_pb.DataSourceState.Finished
        },
        common_pb.DataSourceState.Processing: {
            common_pb.DataSourceState.Failed,
            common_pb.DataSourceState.Finished
        },
        common_pb.DataSourceState.Ready: {
            common_pb.DataSourceState.Failed,
            common_pb.DataSourceState.Init
        },
        common_pb.DataSourceState.Finished: {
            common_pb.DataSourceState.Failed,
            common_pb.DataSourceState.Init,
            common_pb.DataSourceState.Processing
        }
    }

    def __init__(self, peer_client, data_source_name, kvstore, batch_mode):
        self._lock = threading.Lock()
        self._peer_client = peer_client
        self._data_source_name = data_source_name
        self._kvstore = kvstore
        self._batch_mode = batch_mode
        self._init_fsm_action()
        self._data_source = None
        self._sync_data_source()
        self._reset_batch_mode()
        self._raw_data_manifest_manager = RawDataManifestManager(
                kvstore, self._data_source, batch_mode
            )
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
            return self._sync_data_source()

    def set_failed(self):
        return self.set_state(common_pb.DataSourceState.Failed, None)

    def set_state(self, new_state, origin_state=None):
        with self._lock:
            try:
                data_source = self._sync_data_source()
                if data_source.state == new_state:
                    return True
                if origin_state is None or data_source.state == origin_state:
                    data_source.state = new_state
                    self._update_data_source(data_source)
                    return True
                new_data_source = self._sync_data_source()
                logging.warning("DataSource: %s failed to set to state: "
                                "%d, origin state mismatch(%d != %d)",
                                self._data_source_name, new_state,
                                origin_state, new_data_source.state)
                return False
            except Exception as e: # pylint: disable=broad-except
                logging.warning("Faile to set state to %d with exception %s",
                                new_state, e)
                return False

    def start_fsm_worker(self):
        with self._lock:
            if not self._started:
                assert self._fsm_worker is None, \
                    "fsm_woker must be None if FSM is not started"
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
        peer_info = self._get_peer_data_source_status()
        with self._lock:
            data_source = self._sync_data_source()
            state = data_source.state
            if self._fallback_failed_state(peer_info):
                logging.warning("%s at state %d, Peer at state %d "
                                "state invalid! abort data source %s",
                                self._role_repr, state,
                                peer_info.state, self._data_source_name)
            elif state not in self._fsm_driven_handle:
                logging.error("%s at error state %d for data_source %s",
                              self._role_repr, state, self._data_source_name)
            else:
                state_changed = self._fsm_driven_handle[state](peer_info)
                if state_changed:
                    new_state = self._sync_data_source().state
                    logging.warning("%s state changed from %d to %d",
                                    self._role_repr, state, new_state)
                    state = new_state
            if state in (common_pb.DataSourceState.Init,
                         common_pb.DataSourceState.Processing) and \
                    not self._batch_mode:
                self._raw_data_manifest_manager.sub_new_raw_data()

    def _fsm_routine_cond(self):
        return True

    def _sync_data_source(self):
        if self._data_source is None:
            self._data_source = \
                retrieve_data_source(self._kvstore, self._data_source_name)
        assert self._data_source is not None, \
            "data source {} is not in kvstore".format(self._data_source_name)
        return self._data_source

    def _reset_batch_mode(self):
        if self._batch_mode:
            data_source = self._sync_data_source()
            if data_source.state == common_pb.DataSourceState.UnKnown:
                raise RuntimeError("Failed to reset batch mode since "\
                                   "DataSource {} at UnKnown state"\
                                   .format(self._data_source_name))
            if data_source.state in (common_pb.DataSourceState.Init,
                                       common_pb.DataSourceState.Processing):
                logging.info("DataSouce %s at Init/Processing State. Don't "\
                             "need reset", self._data_source_name)
            elif data_source.state == common_pb.DataSourceState.Ready:
                logging.info("DataSouce %s at Ready. need reset to Processing "\
                             "state", self._data_source_name)
                data_source.state = common_pb.DataSourceState.Processing
                self._update_data_source(data_source)
            else:
                raise RuntimeError("Failed to reset batch mode since Data"\
                                   "Source {} at Finished/Failed state, Peer"\
                                   "may delete it"\
                                   .format(self._data_source_name))

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
        if self._batch_mode:
            logging.info("stop fsm from Ready to Finish since "\
                         "the data join master run in batch mode")
            return False
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
            request = dj_pb.DataSourceRequest(
                    data_source_meta=self._data_source_meta
                )
            self._peer_client.AbortDataSource(request)
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
            commit_data_source(self._kvstore, data_source)
        except Exception as e:
            logging.error("Failed to update data source: %s since "\
                          "exception: %s", self._data_source_name, e)
            raise
        self._data_source = data_source
        logging.debug("Success update to update data source: %s.",
                       self._data_source_name)

    def _get_peer_data_source_status(self):
        request = dj_pb.DataSourceRequest(
                data_source_meta=self._data_source_meta
            )
        return self._peer_client.GetDataSourceStatus(request)

    def _all_partition_finished(self):
        all_manifest = self._raw_data_manifest_manager.list_all_manifest()
        assert len(all_manifest) == \
                self._data_source.data_source_meta.partition_num, \
            "manifest number should same with partition number"
        for manifest in all_manifest.values():
            if manifest.sync_example_id_rep.state != \
                    dj_pb.SyncExampleIdState.Synced or \
                    manifest.join_example_rep.state != \
                    dj_pb.JoinExampleState.Joined:
                return False
        return True


class DataJoinMaster(dj_grpc.DataJoinMasterServiceServicer):
    def __init__(self, peer_client, data_source_name,
                 db_database, db_base_dir, db_addr,
                 db_username, db_password, options):
        super(DataJoinMaster, self).__init__()
        self._data_source_name = data_source_name
        kvstore = DBClient(db_database, db_addr, db_username,
                           db_password, db_base_dir, options.use_mock_etcd)
        self._options = options
        self._fsm = MasterFSM(peer_client, data_source_name,
                              kvstore, self._options.batch_mode)
        self._peer_client = peer_client
        self._data_source_meta = self._fsm.get_data_source().data_source_meta
        self._peer_rollback = -1
        self._peer_written = False
        self._local_rollback = -1
        self._local_written = False
        self._rollback = 0
        self._rollback_checked = False
        self._allow_rollback = options.allow_rollback

    def check_rollback(self):
        # allow rollback should be set for both local and peer, otherwise the
        # result is undefined; or we could default to check rollback.
        if not self._allow_rollback:
            self._rollback_checked = True
            return False
        datasource = self._fsm.get_data_source()
        flag_file = os.path.join(datasource.output_base_dir, 'rollback.flag')
        if not tf.gfile.Exists(flag_file):
            logging.info('No local rollback flag found. Syncing with peer.')
            self._local_rollback = 0
        else:
            with tf.gfile.GFile(flag_file, 'rb') as f:
                rollback = timestamp_pb2.Timestamp()
                rollback.ParseFromString(f.read())
            self._local_rollback = max(rollback.seconds, 0)
            logging.info('Local rollback flag found, timestamp %d.',
                         self._local_rollback)
        # both call from peer or response from peer can stop the iteration
        while self._peer_rollback == -1:
            self._rollback_sync_retry()
            # mark as not responding if peer returns -1 or grpc error.
            logging.info('Peer master not responding. Sleep 3s and retry.')
            time.sleep(3)
        logging.info('Peer rollback timestamp: %d.', self._peer_rollback)

        # in case one of the timestamps is 0
        if min(self._local_rollback, self._peer_rollback) == 0:
            self._rollback = max(self._local_rollback, self._peer_rollback)
        else:
            self._rollback = min(self._local_rollback, self._peer_rollback)
        if self._rollback <= 0:
            logging.info('Not rolling back.')
            self._rollback_checked = True
            return False
        # set flag file to every partition on HDFS
        data_dir = os.path.join(datasource.output_base_dir, 'data_block')
        id_dir = os.path.join(datasource.output_base_dir, 'example_dump')
        serialized_timestamp = timestamp_pb2.Timestamp(seconds=self._rollback)\
            .SerializeToString()
        for partition in tf.gfile.ListDirectory(data_dir):
            with tf.gfile.GFile(os.path.join(data_dir, partition,
                                             'rollback.flag'), 'wb') as f:
                f.write(serialized_timestamp)
        for partition in tf.gfile.ListDirectory(id_dir):
            with tf.gfile.GFile(os.path.join(id_dir, partition,
                                             'rollback.flag'), 'wb') as f:
                f.write(serialized_timestamp)
        self._local_written = True
        logging.info('Done setting rollback flag to partitions.')
        # wait for peer to write
        while not self._peer_written:
            self._rollback_sync_retry()
            logging.info('Peer master not yet writes flag. Sleep 3s and retry.')
            time.sleep(3)

        # roll back datasource manifest
        self._fsm.get_mainifest_manager().rollback_manifest()
        logging.info('Done rollback manifests.')
        # remove original flag file
        tf.gfile.Remove(flag_file)
        logging.info('Done removing original flag file.')
        self._rollback_checked = True
        return True

    def _rollback_sync_retry(self):
        try:
            resp = self._peer_client.RollbackSync(
                dj_pb.RollbackSyncRequest(
                    timestamp=timestamp_pb2.Timestamp(
                        seconds=self._local_rollback),
                    written=self._local_written
                )
            )
            self._peer_rollback = max(self._peer_rollback, resp.timestamp)
            self._peer_written = resp.written
        except grpc.RpcError:
            pass

    def RollbackSync(self, request, context):
        self._peer_rollback = max(self._peer_rollback,
                                  request.timestamp.seconds)
        self._peer_written = request.written
        # will send -1 and False to peer if self not yet parse from flag file
        return dj_pb.RollbackSyncResponse(
            timestamp=timestamp_pb2.Timestamp(seconds=self._local_rollback),
            written=self._local_written
        )

    def GetDataSource(self, request, context):
        return self._fsm.get_data_source()

    def GetDataSourceStatus(self, request, context):
        self._check_data_source_meta(request.data_source_meta, True)
        data_source = self._fsm.get_data_source()
        response = dj_pb.DataSourceStatus(
                role=data_source.role,
                state=data_source.state
            )
        return response

    def AbortDataSource(self, request, context):
        response = self._check_data_source_meta(request.data_source_meta)
        if response.code == 0 and not self._fsm.set_failed():
            response.code = -2
            response.error_message = "failed to set failed state to fsm"
        return response

    def RequestJoinPartition(self, request, context):
        response = dj_pb.RawDataResponse()
        if not self._rollback_checked:
            response.status.code = -3
            response.status.error_message = \
                "Master rollback sync not yet finish."
            return response
        meta_status = self._check_data_source_meta(request.data_source_meta)
        if meta_status.code != 0:
            response.status.MergeFrom(meta_status)
            return response
        rank_status = self._check_rank_id(request.rank_id)
        if rank_status.code != 0:
            response.status.MergeFrom(rank_status)
            return response
        data_source = self._fsm.get_data_source()
        if data_source.state != common_pb.DataSourceState.Processing:
            response.status.code = -3
            response.status.error_message = \
                "data source is not at processing state"
        else:
            manifest_manager = self._fsm.get_mainifest_manager()
            rank_id = request.rank_id
            manifest = None
            partition_id = None if request.partition_id < 0 \
                else request.partition_id
            if request.HasField('sync_example_id'):
                manifest = manifest_manager.alloc_sync_exampld_id(
                        rank_id, partition_id
                    )
            elif request.HasField('join_example'):
                manifest = manifest_manager.alloc_join_example(
                        rank_id, partition_id
                    )
            else:
                response.status.code = -4
                response.status.error_message = "request not support"
            if response.status.code == 0:
                response.rollback = timestamp_pb2\
                    .Timestamp(seconds=self._rollback)
                if manifest is not None:
                    response.manifest.MergeFrom(manifest)
                else:
                    assert partition_id is None, \
                        "manifest should not be None if partition id is given."
                    response.finished.MergeFrom(empty_pb2.Empty())
        return response

    def FinishJoinPartition(self, request, context):
        response = self._check_data_source_meta(request.data_source_meta)
        if response.code != 0:
            return response
        response = self._check_rank_id(request.rank_id)
        if response.code != 0:
            return response
        data_source = self._fsm.get_data_source()
        if data_source.state != common_pb.DataSourceState.Processing:
            response.code = -2
            response.error_message = "data source is not at processing state"
        else:
            rank_id = request.rank_id
            partition_id = request.partition_id
            manifest_manager = self._fsm.get_mainifest_manager()
            if request.HasField('sync_example_id'):
                manifest_manager.finish_sync_example_id(rank_id, partition_id)
            elif request.HasField('join_example'):
                manifest_manager.finish_join_example(rank_id, partition_id)
            else:
                response.code = -3
                response.error_message = "request not support"
        return response

    def QueryRawDataManifest(self, request, context):
        self._check_data_source_meta(request.data_source_meta, True)
        manifest_manager = self._fsm.get_mainifest_manager()
        manifest = manifest_manager.get_manifest(request.partition_id)
        return manifest

    def FinishRawData(self, request, context):
        response = self._check_data_source_meta(request.data_source_meta)
        if response.code == 0:
            if self._options.batch_mode:
                response.code = -2
                response.error_message = "Forbid to finish raw data since "\
                                         "master run in batch mode"
            elif request.HasField('finish_raw_data'):
                manifest_manager = self._fsm.get_mainifest_manager()
                manifest_manager.finish_raw_data(request.partition_id)
            else:
                response.code = -3
                response.error_message = \
                    "FinishRawData should has finish_raw_data"
        return response

    def AddRawData(self, request, context):
        response = self._check_data_source_meta(request.data_source_meta)
        if response.code == 0:
            sub_dir = self._fsm.get_data_source().raw_data_sub_dir
            if self._options.batch_mode:
                response.code = -2
                response.error_message = "Forbid to add raw data since "\
                                         "master run in batch mode"
            elif request.HasField('added_raw_data_metas'):
                manifest_manager = self._fsm.get_mainifest_manager()
                manifest_manager.add_raw_data(
                        request.partition_id,
                        request.added_raw_data_metas.raw_data_metas,
                        request.added_raw_data_metas.dedup
                    )
            else:
                response.code = -3
                response.error_message = \
                        "AddRawData should has field next_process_index"
        return response

    def ForwardPeerDumpedIndex(self, request, context):
        response = self._check_data_source_meta(request.data_source_meta)
        if response.code == 0:
            manifest_manager = self._fsm.get_mainifest_manager()
            if request.HasField('peer_dumped_index'):
                manifest_manager.forward_peer_dumped_index(
                        request.partition_id,
                        request.peer_dumped_index.peer_dumped_index
                    )
            else:
                response.code = -2
                response.error_message = "ForwardPeerDumpedIndex should "\
                                         "has field peer_dumped_index"
        return response

    def GetRawDataLatestTimeStamp(self, request, context):
        response = dj_pb.RawDataResponse(
                timestamp=timestamp_pb2.Timestamp(seconds=0)
            )
        meta_status = self._check_data_source_meta(request.data_source_meta)
        if meta_status.code != 0:
            response.status.MergeFrom(meta_status)
            return response
        manifest_manager = self._fsm.get_mainifest_manager()
        ts = manifest_manager.get_raw_date_latest_timestamp(
                request.partition_id
            )
        if ts is not None:
            response.timestamp.MergeFrom(ts)
        return response

    def _check_data_source_meta(self, remote_meta, raise_exp=False):
        if self._data_source_meta != remote_meta:
            local_meta = self._data_source_meta
            if local_meta.name != remote_meta.name:
                logging.error("data_source_meta mismtach since name "\
                              "%s != %s", local_meta.name, remote_meta.name)
            if local_meta.partition_num != remote_meta.partition_num:
                logging.error("data_source_meta mismatch since partition "\
                              "num %d != %d", local_meta.partition_num,
                              remote_meta.partition_num)
            if local_meta.start_time != remote_meta.start_time:
                logging.error("data_source_meta mismatch since start_time "\
                              "%d != %d",
                              local_meta.start_time, remote_meta.start_time)
            if local_meta.end_time != remote_meta.end_time:
                logging.error("data_source_meta mismatch since end_time "\
                              "%d != %d",
                              local_meta.end_time, remote_meta.end_time)
            if local_meta.negative_sampling_rate != \
                    remote_meta.negative_sampling_rate:
                logging.error("data_source_meta mismatch since negative_"\
                              "sampling_rate %f != %f",
                              local_meta.negative_sampling_rate,
                              remote_meta.negative_sampling_rate)
            if raise_exp:
                raise RuntimeError("data source meta mismatch")
            return common_pb.Status(
                    code=-1, error_message="data source meta mismatch"
                )
        return common_pb.Status(code=0)

    def _check_rank_id(self, rank_id):
        if rank_id < 0:
            return common_pb.Status(
                    code=-2, error_message="invalid rank id"
                )
        return common_pb.Status(code=0)

    def start_fsm(self):
        self._fsm.start_fsm_worker()
        self.check_rollback()

    def stop_fsm(self):
        self._fsm.stop_fsm_worker()

class DataJoinMasterService(object):
    def __init__(self, listen_port, peer_addr, data_source_name,
                 db_database, db_base_dir, db_addr,
                 db_username, db_password, options):
        channel = make_insecure_channel(
                peer_addr, ChannelType.REMOTE,
                options=[('grpc.max_send_message_length', 2**31-1),
                         ('grpc.max_receive_message_length', 2**31-1)]
            )
        peer_client = dj_grpc.DataJoinMasterServiceStub(channel)
        self._data_source_name = data_source_name
        self._listen_port = listen_port
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        self._data_join_master = DataJoinMaster(
                peer_client, data_source_name, db_database,
                db_base_dir, db_addr, db_username,
                db_password, options
            )
        dj_grpc.add_DataJoinMasterServiceServicer_to_server(
                self._data_join_master, self._server
            )
        self._server.add_insecure_port('[::]:%d'%listen_port)
        self._server_started = False

    def start(self):
        if not self._server_started:
            self._server.start()
            self._data_join_master.start_fsm()
            self._server_started = True
            logging.info("DataJoinMasterService for data_source: " \
                         "%s start on port[%d]", self._data_source_name,
                         self._listen_port)

    def stop(self):
        if self._server_started:
            self._data_join_master.stop_fsm()
            self._server.stop(None)
            self._server_started = False
            logging.info("DataJoinMasterService for data_source: %s "\
                         "stopped ", self._data_source_name)

    def run(self):
        self.start()
        self._server.wait_for_termination()
        self.stop()

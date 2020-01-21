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

import threading
import logging
from enum import Enum

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.joiner_impl import create_example_joiner

class _JoinState(Enum):
    ALLOC_JOIN_PARTITION = 0
    JOIN_EXAMPLE = 1

class ExampleJoinLeader(object):
    def __init__(self, peer_client, master_client,
                 rank_id, etcd, data_source, options):
        self._lock = threading.Lock()
        self._peer_client = peer_client
        self._master_client = master_client
        self._rank_id = rank_id
        self._etcd = etcd
        self._data_source = data_source
        self._options = options
        self._started = False
        self._state = None
        self._processing_manifest = None
        self._joiner = None

    def start_routine_workers(self):
        with self._lock:
            if not self._started:
                self._worker_map = {
                    'join_partition_allocator': RoutineWorker(
                    'join_partition_allocator',
                    self._allocate_join_partition_fn,
                    self._allocate_join_partition_cond, 5),

                    'leader_example_joiner': RoutineWorker(
                    'leader_example_joiner',
                    self._join_leader_example_fn,
                    self._join_leader_example_cond, 5),

                    'data_block_meta_syncer': RoutineWorker(
                    'data_block_meta_syncer',
                    self._sync_data_block_meta_fn,
                    self._sync_data_block_meta_cond, 5),
                }
                for _, w in self._worker_map.items():
                    w.start_routine()
                self._state = _JoinState.ALLOC_JOIN_PARTITION
                self._started = True

    def stop_routine_workers(self):
        wait_join = True
        with self._lock:
            if self._started:
                wait_join = True
                self._started = False
        if wait_join:
            for w in self._worker_map.values():
                w.stop_routine()

    def _wakeup_join_partition_allocator(self):
        self._state = _JoinState.ALLOC_JOIN_PARTITION
        self._processing_manifest = None
        self._worker_map['join_partition_allocator'].wakeup()

    def _allocate_join_partition_fn(self):
        assert self._processing_manifest is None
        req = dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                join_example=dj_pb.JoinExampleRequest(
                    partition_id=-1
                )
            )
        rsp = self._master_client.RequestJoinPartition(req)
        if rsp.status.code != 0:
            raise RuntimeError("Failed to Request partition for "\
                               "example intsesection, error msg {}".format(
                                rsp.status.error_message))
        if rsp.HasField('finished'):
            with self._lock:
                self._state = None
                return
        if not rsp.HasField('manifest'):
            logging.warning(
                    "no manifest is at state %d, wait and retry",
                    dj_pb.RawDataState.Synced
                )
            return
        joiner = create_example_joiner(
                self._options, self._etcd, self._data_source,
                rsp.manifest.partition_id, self._options
            )
        with self._lock:
            self._processing_manifest = rsp.manifest
            self._joiner = joiner
            self._check_manifest()
            self._wakeup_leader_example_joiner()
            self._wakeup_data_block_meta_syncer()

    def _allocate_join_partition_cond(self):
        with self._lock:
            return (self._state == _JoinState.ALLOC_JOIN_PARTITION
                    and (self._processing_manifest is None or
                         self._joiner is None))

    def _check_manifest(self):
        assert self._processing_manifest is not None
        assert self._processing_manifest.allocated_rank_id == self._rank_id
        assert self._processing_manifest.state == dj_pb.RawDataState.Joining

    def _wakeup_leader_example_joiner(self):
        self._state = _JoinState.JOIN_EXAMPLE
        self._worker_map['leader_example_joiner'].wakeup()

    def _join_leader_example_fn(self):
        joiner = None
        with self._lock:
            joiner = self._joiner
        if joiner is not None and not joiner.join_finished():
            joiner.join_example()

    def _join_leader_example_cond(self):
        with self._lock:
            return (self._state == _JoinState.JOIN_EXAMPLE and
                    self._processing_manifest is not None and
                    self._joiner and not None and
                    not self._joiner.join_finished())

    def _wakeup_data_block_meta_syncer(self):
        self._state = _JoinState.JOIN_EXAMPLE
        self._worker_map['data_block_meta_syncer'].wakeup()

    def _sync_data_block_meta_fn(self):
        next_index, follower_finished = self._start_leader_partition()
        join_finished = False
        try:
            join_finished = False
            while not follower_finished:
                (meta, join_finished) = (
                        self._joiner.get_data_block_meta(next_index)
                    )
                if meta is None:
                    break
                self._send_leader_data_block_meta(meta)
                next_index += 1
        except Exception as e: # pylint: disable=broad-except
            # reset sync state
            logging.error("Failed to call Leader CreateDataBlock: %s", e)
        else:
            if ((join_finished or follower_finished) and
                    self._finish_join_partition(follower_finished)):
                with self._lock:
                    self._wakeup_join_partition_allocator()

    def _sync_data_block_meta_cond(self):
        with self._lock:
            return (self._state == _JoinState.JOIN_EXAMPLE and
                    self._processing_manifest is not None and
                    self._joiner and not None)

    def _start_leader_partition(self):
        assert self._processing_manifest is not None
        req = dj_pb.LeaderStartPartitionRequest(
            data_source_meta=self._data_source.data_source_meta,
            partition_id=self._processing_manifest.partition_id
        )
        rsp = self._peer_client.StartPartition(req)
        if rsp.status.code != 0:
            raise RuntimeError(
                    "Failed to call Leader for start to sync data block meta "\
                    "for partition {}, reason {}".format(
                    self._processing_manifest.partition_id,
                    rsp.status.error_message)
                )
        return rsp.next_data_block_index, rsp.finished

    def _send_leader_data_block_meta(self, meta):
        req = dj_pb.CreateDataBlockRequest(
                data_source_meta=self._data_source.data_source_meta,
                data_block_meta=meta
            )
        rsp = self._peer_client.CreateDataBlock(req)
        if rsp.code != 0:
            raise RuntimeError(
                    "Follower refuse create data block {} indexed as {},"\
                    "reason {}".format(meta.block_id,
                    meta.data_block_index, rsp.error_message)
                )

    def _finish_join_partition(self, follower_finished):
        if not follower_finished:
            req = dj_pb.LeaderFinishPartitionRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    partition_id=self._processing_manifest.partition_id,
                )
            rsp = self._peer_client.FinishPartition(req)
            if rsp.status.code != 0:
                raise RuntimeError(
                        "Failed to call Leader finish partition "\
                        "reason: {}".format(rsp.status.error_message)
                )
            follower_finished = rsp.finished

        if follower_finished:
            req = dj_pb.FinishRawDataRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    rank_id=self._rank_id,
                    join_example=dj_pb.JoinExampleRequest(
                        partition_id=self._processing_manifest.partition_id,
                    )
                )
            rsp = self._master_client.FinishJoinPartition(req)
            if rsp.code != 0:
                raise RuntimeError(
                        "Failed to finish raw data from joining. "\
                        "reason: %s" % rsp.error_message
                    )
            return True
        logging.warning("Leader is creating data block, waitiing")
        return False

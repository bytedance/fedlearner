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
import os
from enum import Enum

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.raw_data_visitor import RawDataVisitor

class _SyncState(Enum):
    ALLOC_SYNC_PARTITION = 0
    SYNC_EXAMPLE_ID = 1

class ExampleIdSyncLeader(object):
    def __init__(self, peer_client, master_client,
                 rank_id, etcd, data_source, options):
        self._lock = threading.Lock()
        self._peer_client = peer_client
        self._master_client = master_client
        self._rank_id = rank_id
        self._etcd = etcd
        self._data_source = data_source
        self._options = options
        self._state = None
        self._processing_manifest = None
        self._raw_data_visitor = None
        self._started = False
        self._partition_end_index = None

    def start_routine_workers(self):
        with self._lock:
            if not self._started:
                self._worker_map = {
                    'sync_partition_allocator': RoutineWorker(
                    'sync_partition_allocator',
                    self._allocate_sync_partition_fn,
                    self._allocate_sync_partition_cond, 5),

                    'follower_example_id_syncer': RoutineWorker(
                    'follower_example_id_syncer',
                    self._sync_follower_example_id_fn,
                    self._sync_follower_example_id_cond, 5),
                }
                for _, w in self._worker_map.items():
                    w.start_routine()
                self._state = _SyncState.ALLOC_SYNC_PARTITION
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

    def _wakeup_sync_partition_allocator(self):
        self._state = _SyncState.ALLOC_SYNC_PARTITION
        self._processing_manifest = None
        self._raw_data_visitor = None
        self._partition_end_index = None
        self._worker_map['sync_partition_allocator'].wakeup()

    def _allocate_sync_partition_fn(self):
        assert self._processing_manifest is None
        req = dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                sync_example_id=dj_pb.SyncExampleIdRequest(
                    partition_id=-1
                )
            )
        rsp = self._master_client.RequestJoinPartition(req)
        if rsp.status.code != 0:
            raise RuntimeError("Failed to Request partition for sync "\
                               "id to follower, error msg {}".format(
                                rsp.status.error_message))
        if rsp.HasField('finished'):
            with self._lock:
                self._state = None
                return
        if not rsp.HasField('manifest'):
            logging.warning(
                    "no manifest is at state %d, wait and retry",
                    dj_pb.RawDataState.UnAllocated
                )
            return
        rdv = RawDataVisitor(
                self._etcd, self._data_source,
                rsp.manifest.partition_id, self._options
            )
        with self._lock:
            self._processing_manifest = rsp.manifest
            self._raw_data_visitor = rdv
            self._check_manifest()
            self._wakeup_follower_example_id_syncer()

    def _allocate_sync_partition_cond(self):
        with self._lock:
            return (self._state == _SyncState.ALLOC_SYNC_PARTITION and
                    (self._processing_manifest is None or
                     self._raw_data_visitor is None))

    def _check_manifest(self):
        assert self._processing_manifest is not None
        assert self._processing_manifest.allocated_rank_id == self._rank_id
        assert self._processing_manifest.state == dj_pb.RawDataState.Syncing

    def _wakeup_follower_example_id_syncer(self):
        self._state = _SyncState.SYNC_EXAMPLE_ID
        self._partition_end_index = None
        self._worker_map['follower_example_id_syncer'].wakeup()

    def _sync_follower_example_id_fn(self):
        next_index, finished = self._start_follower_partition()
        if (not finished and (self._partition_end_index is None or
                next_index <= self._partition_end_index)):
            try:
                if next_index == 0:
                    self._raw_data_visitor.reset()
                else:
                    self._raw_data_visitor.seek(next_index-1)
            except StopIteration:
                assert self._raw_data_visitor.finished()
            else:
                begin_index = next_index
                expected_index = next_index
                items = []
                for (index, item) in self._raw_data_visitor:
                    if index != expected_index:
                        logging.fatal("index is not consecutive, %d != %d",
                                      index, expected_index)
                        os._exit(-1) # pylint: disable=protected-access
                    items.append(item)
                    expected_index += 1
                    if len(items) > 2048:
                        self._send_follower_example_ids(items, begin_index)
                        items = []
                        begin_index = expected_index
                if len(items) > 0:
                    self._send_follower_example_ids(items, begin_index)
            assert self._raw_data_visitor.finished()
            self._partition_end_index = (
                    self._raw_data_visitor.get_current_index()
                )

        if self._finish_sync_partition(finished):
            with self._lock:
                self._wakeup_sync_partition_allocator()

    def _sync_follower_example_id_cond(self):
        with self._lock:
            return self._state == _SyncState.SYNC_EXAMPLE_ID

    def _start_follower_partition(self):
        assert self._processing_manifest is not None
        req = dj_pb.FollowerStartPartitionRequest(
            data_source_meta=self._data_source.data_source_meta,
            partition_id=self._processing_manifest.partition_id
        )
        rsp = self._peer_client.StartPartition(req)
        if rsp.status.code != 0:
            raise RuntimeError(
                    "Failed to call Follower for start to sync id for "\
                    "partition {}, reason {}".format(
                    self._processing_manifest.partition_id,
                    rsp.status.error_message)
                )
        return rsp.next_index, rsp.finished

    def _send_follower_example_ids(self, items, begin_index):
        if len(items) == 0:
            return
        req = dj_pb.SyncExamplesRequest(
                data_source_meta=self._data_source.data_source_meta,
                partition_id=self._processing_manifest.partition_id,
                begin_index=begin_index
            )
        for item in items:
            example_id = item.example_id
            event_time = item.event_time
            req.example_id.append(example_id)
            req.event_time.append(event_time)
        rsp = self._peer_client.SyncExamples(req)
        if rsp.code != 0:
            raise RuntimeError(
                    "Follower refuse sync {} example ids start from {},"\
                    "reason {}".format(len(items), begin_index,
                    rsp.error_message)
                )

    def _finish_sync_partition(self, follower_finished):
        if not follower_finished:
            req = dj_pb.FollowerFinishPartitionRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    partition_id=self._processing_manifest.partition_id,
                )
            rsp = self._peer_client.FinishPartition(req)
            if rsp.status.code != 0:
                raise RuntimeError(
                        "Failed to call Follower finish partition "\
                        "reason: {}".format(rsp.status.error_message)
                )
            follower_finished = rsp.finished
        if follower_finished:
            req = dj_pb.FinishRawDataRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    rank_id=self._rank_id,
                    sync_example_id=dj_pb.SyncExampleIdRequest(
                        partition_id=self._processing_manifest.partition_id,
                    )
                )
            rsp = self._master_client.FinishJoinPartition(req)
            if rsp.code != 0:
                raise RuntimeError(
                        "Failed to finish raw data from syncing. "\
                        "reason: %s" % rsp.error_message
                    )
            return True
        logging.warning("Follower is dumping example id, waitiing")
        return False

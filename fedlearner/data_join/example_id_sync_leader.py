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
from contextlib import contextmanager

from google.protobuf import empty_pb2

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.raw_data_visitor import RawDataVisitor

class ExampleIdSyncLeader(object):
    class ImplContext(object):
        def __init__(self, etcd, data_source,
                     raw_data_manifest, raw_data_options):
            self.raw_data_manifest = raw_data_manifest
            self.raw_data_visitor = RawDataVisitor(
                    etcd, data_source,
                    raw_data_manifest.partition_id,
                    raw_data_options
                )
            self.stale_with_follower = True
            self.follower_finished = False
            self.raw_data_finished = raw_data_manifest.finished

        @property
        def partition_id(self):
            return self.raw_data_manifest.partition_id

        def acquire_stale_with_follower(self):
            self.stale_with_follower = True

        def release_stale_with_follower(self):
            self.stale_with_follower = False

    def __init__(self, peer_client, master_client,
                 rank_id, etcd, data_source, raw_data_options):
        self._lock = threading.Lock()
        self._peer_client = peer_client
        self._master_client = master_client
        self._rank_id = rank_id
        self._etcd = etcd
        self._data_source = data_source
        self._raw_data_options = raw_data_options
        self._unsynced_partition_exhausted = False
        self._impl_ctx = None
        self._started = False

    def start_routine_workers(self):
        with self._lock:
            if not self._started:
                self._worker_map = {
                    'unsynced_partition_allocator': RoutineWorker(
                    'unsynced_partition_allocator',
                    self._allocate_unsynced_partition_fn,
                    self._allocate_unsynced_partition_cond, 5),

                    'example_id_syncer': RoutineWorker(
                    'example_id_syncer',
                    self._sync_example_id_fn,
                    self._sync_example_id_cond, 5),
                }
                for _, w in self._worker_map.items():
                    w.start_routine()
                self._started = True
                self._wakeup_unsynced_partition_allocator()

    def stop_routine_workers(self):
        wait_join = True
        with self._lock:
            if self._started:
                wait_join = True
                self._started = False
        if wait_join:
            for w in self._worker_map.values():
                w.stop_routine()

    def _wakeup_unsynced_partition_allocator(self):
        self._impl_ctx = None
        self._worker_map['unsynced_partition_allocator'].wakeup()

    def _allocate_unsynced_partition_fn(self):
        req = dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                partition_id=-1,
                sync_example_id=empty_pb2.Empty()
            )
        rsp = self._master_client.RequestJoinPartition(req)
        if rsp.status.code != 0:
            raise RuntimeError(
                    "Failed to Request partition for sync id to " \
                    "follower, error msg {}".format(rsp.status.error_message)
                )
        if rsp.HasField('finished'):
            self._set_unsynced_partition_exhausted()
            return
        assert rsp.HasField('manifest'), "rsp of RequestJoinPartition must "\
                                         "has manifest if not finished"
        impl_ctx = ExampleIdSyncLeader.ImplContext(
                self._etcd, self._data_source,
                rsp.manifest, self._raw_data_options
            )
        with self._lock:
            assert self._impl_ctx is None
            self._impl_ctx = impl_ctx
            self._wakeup_example_id_syncer()

    def _allocate_unsynced_partition_cond(self):
        with self._lock:
            return self._impl_ctx is None and \
                    not self._unsynced_partition_exhausted

    def _set_unsynced_partition_exhausted(self):
        with self._lock:
            self._unsynced_partition_exhausted = True

    def _wakeup_example_id_syncer(self):
        self._worker_map['example_id_syncer'].wakeup()

    def _sync_example_id_fn(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleIdSyncLeader.ImplContext)
        self._sniff_raw_data_finished(impl_ctx)
        if not impl_ctx.follower_finished:
            with self._sync_example_id_impl(impl_ctx) as syncer:
                impl_ctx.follower_finished = syncer()
        if impl_ctx.raw_data_finished:
            if self._finish_sync_example_id(impl_ctx):
                self._wakeup_unsynced_partition_allocator()

    def _sync_example_id_cond(self):
        with self._lock:
            if self._impl_ctx is not None:
                self._worker_map['example_id_syncer'].setup_args(
                        self._impl_ctx
                    )
            return self._impl_ctx is not None

    def _sniff_raw_data_finished(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleIdSyncLeader.ImplContext)
        if not impl_ctx.raw_data_finished:
            req = dj_pb.RawDataRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    rank_id=self._rank_id,
                    partition_id=impl_ctx.partition_id
                )
            manifest = self._master_client.QueryRawDataManifest(req)
            impl_ctx.raw_data_finished = manifest.finished

    @contextmanager
    def _sync_example_id_impl(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleIdSyncLeader.ImplContext)
        impl_ctx.acquire_stale_with_follower()

        def syncer():
            next_index, follower_finished = \
                    self._start_sync_example_id(impl_ctx)
            if follower_finished:
                return True
            impl_ctx.raw_data_visitor.active_visitor()
            assert next_index >= 0, "the next index should >= 0"
            if next_index == 0:
                impl_ctx.raw_data_visitor.reset()
            else:
                impl_ctx.raw_data_visitor.seek(next_index-1)
            begin_index = next_index
            expected_index = next_index
            items = []
            for (index, item) in impl_ctx.raw_data_visitor:
                if index != expected_index:
                    logging.fatal("index is not consecutive, %d != %d",
                                  index, expected_index)
                    os._exit(-1) # pylint: disable=protected-access
                items.append(item)
                expected_index += 1
                if len(items) > 2048:
                    self._send_example_ids(items, begin_index, impl_ctx)
                    items = []
                    begin_index = expected_index
            if len(items) > 0:
                self._send_example_ids(items, begin_index, impl_ctx)
            assert impl_ctx.raw_data_visitor.finished(), \
                "the raw data visitor should be finihed "\
                "if not error meets in syncer"
            return False
        yield syncer

        impl_ctx.release_stale_with_follower()

    def _start_sync_example_id(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleIdSyncLeader.ImplContext)
        req = dj_pb.StartPartitionRequest(
            data_source_meta=self._data_source.data_source_meta,
            rank_id=self._rank_id,
            partition_id=impl_ctx.partition_id
        )
        rsp = self._peer_client.StartPartition(req)
        if rsp.status.code != 0:
            raise RuntimeError(
                    "Failed to call Follower for start to sync id for "\
                    "partition {}, reason {}".format(
                    impl_ctx.partition_id, rsp.status.error_message)
                )
        return rsp.next_index, rsp.finished

    def _send_example_ids(self, items, begin_index, impl_ctx):
        assert isinstance(impl_ctx, ExampleIdSyncLeader.ImplContext)
        if len(items) == 0:
            return
        sync_content = dj_pb.SyncContent(
                lite_example_ids=dj_pb.LiteExampleIds(
                    partition_id=impl_ctx.partition_id,
                    begin_index=begin_index
                )
            )
        for item in items:
            sync_content.lite_example_ids.example_id.append(item.example_id)
            sync_content.lite_example_ids.event_time.append(item.event_time)
        req = dj_pb.SyncPartitionRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                partition_id=impl_ctx.partition_id,
                compressed=False,
                content_bytes=sync_content.SerializeToString()
            )
        rsp = self._peer_client.SyncPartition(req)
        if rsp.code != 0:
            raise RuntimeError(
                    "Follower refuse sync {} example ids start from {},"\
                    "reason {}".format(len(items), begin_index,
                    rsp.error_message)
                )

    def _finish_sync_example_id(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleIdSyncLeader.ImplContext)
        if not impl_ctx.follower_finished:
            req = dj_pb.FinishPartitionRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    rank_id=self._rank_id,
                    partition_id=impl_ctx.partition_id
                )
            rsp = self._peer_client.FinishPartition(req)
            if rsp.status.code != 0:
                raise RuntimeError(
                        "Failed to call Follower finish partition " \
                        "reason: {}".format(rsp.status.error_message)
                )
            impl_ctx.follower_finished = rsp.finished
        if not impl_ctx.follower_finished:
            logging.debug("Follower is still dumping example id " \
                          "for partition %d waitiing", impl_ctx.partition_id)
            return False

        logging.debug("Follower has been synced example ids " \
                      "for partition %d", impl_ctx.partition_id)
        req = dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                partition_id=impl_ctx.partition_id,
                sync_example_id=empty_pb2.Empty()
            )
        rsp = self._master_client.FinishJoinPartition(req)
        if rsp.code != 0:
            raise RuntimeError(
                    "Failed to finish raw data from syncing. "\
                    "reason: %s" % rsp.error_message
                )
        logging.debug("Leader has been synced example ids " \
                      "for partition %d", impl_ctx.partition_id)
        return True

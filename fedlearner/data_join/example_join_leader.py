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
import zlib
from contextlib import contextmanager

from google.protobuf import empty_pb2

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.joiner_impl import create_example_joiner

class ExampleJoinLeader(object):
    class ImplContext(object):
        def __init__(self, etcd, data_source, raw_data_manifest,
                     example_joiner_options, raw_data_options):
            self.raw_data_manifest = raw_data_manifest
            self.example_joiner = create_example_joiner(
                    example_joiner_options, raw_data_options,
                    etcd, data_source, raw_data_manifest.partition_id,
                )
            self.stale_with_leader = True
            self.next_data_block_index = 0
            self.leader_finished = False

        @property
        def partition_id(self):
            return self.raw_data_manifest.partition_id

        def acquire_stale_with_leader(self):
            self.stale_with_leader = True

        def release_stale_with_leader(self):
            self.stale_with_leader = False

        def get_next_data_block_meta(self):
            assert self.next_data_block_index >= 0
            return self.example_joiner.get_data_block_meta_by_index(
                    self.next_data_block_index
                )

        def __getattr__(self, attr):
            return getattr(self.example_joiner, attr)

    def __init__(self, peer_client, master_client, rank_id, etcd,
                 data_source, raw_data_options, example_joiner_options):
        self._lock = threading.Lock()
        self._peer_client = peer_client
        self._master_client = master_client
        self._rank_id = rank_id
        self._etcd = etcd
        self._data_source = data_source
        self._raw_data_options = raw_data_options
        self._example_joiner_options = example_joiner_options
        self._unjoined_partition_exhausted = False
        self._impl_ctx = None
        self._started = False

    def start_routine_workers(self):
        with self._lock:
            if not self._started:
                self._worker_map = {
                    'unjoined_partition_allocator': RoutineWorker(
                    'unjoined_partition_allocator',
                    self._allocate_unjoined_partition_fn,
                    self._allocate_unjoined_partition_cond, 5),

                    'example_joiner': RoutineWorker(
                    'example_joiner',
                    self._join_example_fn,
                    self._join_example_cond, 5),

                    'data_block_meta_syncer': RoutineWorker(
                    'data_block_meta_syncer',
                    self._sync_data_block_meta_fn,
                    self._sync_data_block_meta_cond, 5),
                }
                for _, w in self._worker_map.items():
                    w.start_routine()
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

    def _wakeup_unjoined_partition_allocator(self):
        self._impl_ctx = None
        self._worker_map['unjoined_partition_allocator'].wakeup()

    def _allocate_unjoined_partition_fn(self):
        req = dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                partition_id=-1,
                join_example=empty_pb2.Empty()
            )
        rsp = self._master_client.RequestJoinPartition(req)
        if rsp.status.code != 0:
            raise RuntimeError(
                    "Failed to Request partition for "\
                    "joining example, error msg {}".format(
                    rsp.status.error_message)
                )
        if rsp.HasField('finished'):
            self._set_unjoined_partition_exhausted()
            return

        assert rsp.HasField('manifest')
        impl_ctx = ExampleJoinLeader.ImplContext(
                self._etcd, self._data_source, rsp.manifest,
                self._example_joiner_options, self._raw_data_options
            )
        with self._lock:
            assert self._impl_ctx is None
            self._impl_ctx = impl_ctx
            self._wakeup_example_joiner()
            self._wakeup_data_block_meta_syncer()

    def _allocate_unjoined_partition_cond(self):
        with self._lock:
            return self._impl_ctx is None and \
                    not self._unjoined_partition_exhausted

    def _set_unjoined_partition_exhausted(self):
        with self._lock:
            self._unjoined_partition_exhausted = True

    def _wakeup_example_joiner(self):
        self._worker_map['example_joiner'].wakeup()

    def _join_example_fn(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleJoinLeader.ImplContext)
        self._sniff_join_data_finished(impl_ctx)
        if impl_ctx.need_join():
            with impl_ctx.make_example_joiner() as joiner:
                for data_block_meta in joiner:
                    if data_block_meta is None:
                        continue
                    self._wakeup_data_block_meta_syncer()

    def _join_example_cond(self):
        with self._lock:
            if self._impl_ctx is not None:
                self._worker_map['example_joiner'].setup_args(self._impl_ctx)
            return self._impl_ctx is not None

    def _sniff_join_data_finished(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleJoinLeader.ImplContext)
        if not impl_ctx.is_sync_example_id_finished() or \
                not impl_ctx.is_raw_data_finished():
            req = dj_pb.RawDataRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    rank_id=self._rank_id,
                    partition_id=impl_ctx.partition_id
                )
            manifest = self._master_client.QueryRawDataManifest(req)
            if manifest.sync_example_id_rep.state == \
                    dj_pb.SyncExampleIdState.Synced:
                impl_ctx.set_sync_example_id_finished()
            if manifest.finished:
                impl_ctx.set_raw_data_finished()

    def _wakeup_data_block_meta_syncer(self):
        self._worker_map['data_block_meta_syncer'].wakeup()

    def _sync_data_block_meta_fn(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleJoinLeader.ImplContext)
        joined_finished = False
        if not impl_ctx.leader_finished:
            with self._sync_data_block_meta_impl(impl_ctx) as syncer:
                joined_finished = syncer()
        if joined_finished or impl_ctx.leader_finished:
            if self._finish_sync_data_block_meta(impl_ctx):
                self._wakeup_unjoined_partition_allocator()

    def _sync_data_block_meta_cond(self):
        with self._lock:
            if self._impl_ctx is not None:
                self._worker_map['data_block_meta_syncer'].setup_args(
                        self._impl_ctx
                    )
            return self._impl_ctx is not None

    @contextmanager
    def _sync_data_block_meta_impl(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleJoinLeader.ImplContext)
        impl_ctx.acquire_stale_with_leader()

        def syncer():
            impl_ctx.next_data_block_index, impl_ctx.leader_finished = \
                    self._start_sync_data_block_meta(impl_ctx)
            join_finished = False
            while not impl_ctx.leader_finished:
                join_finished, meta = impl_ctx.get_next_data_block_meta()
                if meta is None:
                    break
                self._send_data_block_meta(meta)
                impl_ctx.next_data_block_index += 1
            return join_finished
        yield syncer

        impl_ctx.release_stale_with_leader()

    def _start_sync_data_block_meta(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleJoinLeader.ImplContext)
        req = dj_pb.StartPartitionRequest(
            data_source_meta=self._data_source.data_source_meta,
            rank_id=self._rank_id,
            partition_id=impl_ctx.partition_id
        )
        rsp = self._peer_client.StartPartition(req)
        if rsp.status.code != 0:
            raise RuntimeError(
                    "Failed to call Leader for start to sync data "
                    "block meta for partition {}, reason {}".format(
                    impl_ctx.partition_id, rsp.status.error_message)
                )
        return rsp.next_index, rsp.finished

    def _send_data_block_meta(self, meta):
        serialize_bytes = \
            dj_pb.SyncContent(data_block_meta=meta).SerializeToString()
        req = dj_pb.SyncPartitionRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                content_bytes=serialize_bytes,
                compressed=False
            )
        if len(serialize_bytes) > (2 << 20):
            compressed_bytes = zlib.compress(serialize_bytes, 5)
            if len(compressed_bytes) < len(serialize_bytes) * 0.8:
                req.content_bytes = compressed_bytes
                req.compressed = True
        rsp = self._peer_client.SyncPartition(req)
        if rsp.code != 0:
            raise RuntimeError(
                    "Leader refuse data block {} indexed as {},"\
                    "reason {}".format(meta.block_id,
                    meta.data_block_index, rsp.error_message)
                )

    def _finish_sync_data_block_meta(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleJoinLeader.ImplContext)
        assert impl_ctx.is_join_finished()
        if not impl_ctx.leader_finished:
            req = dj_pb.FinishPartitionRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    rank_id=self._rank_id,
                    partition_id=impl_ctx.partition_id
                )
            rsp = self._peer_client.FinishPartition(req)
            if rsp.status.code != 0:
                raise RuntimeError(
                        "Failed to call Leader finish partition "\
                        "reason: {}".format(rsp.status.error_message)
                    )
            impl_ctx.leader_finished = rsp.finished

        if not impl_ctx.leader_finished:
            logging.debug("Leader is still dumping data block for " \
                          "partition %d waitiing", impl_ctx.partition_id)
            return False
        logging.debug("Leader has been synced data block meta" \
                      "for partition %d", impl_ctx.partition_id)
        req = dj_pb.RawDataRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    rank_id=self._rank_id,
                    partition_id=impl_ctx.partition_id,
                    join_example=empty_pb2.Empty()
                )
        rsp = self._master_client.FinishJoinPartition(req)
        if rsp.code != 0:
            raise RuntimeError("Failed to finish raw data from joining. "\
                               "reason: %s" % rsp.error_message)
        logging.debug("Follower has been synced data block meta for " \
                      "partition %d. reset impl_ctx", impl_ctx.partition_id)
        return True

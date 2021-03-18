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
import threading

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import metrics

from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join import common

class TransmitLeader(object):
    class ImplContext(object):
        def __init__(self, raw_data_manifest):
            self._lock = threading.Lock()
            self.raw_data_manifest = raw_data_manifest
            self.peer_finished = False
            self.peer_dumped_index = raw_data_manifest.peer_dumped_index
            self.peer_next_index = None

        @property
        def partition_id(self):
            return self.raw_data_manifest.partition_id

        def set_peer_index(self, peer_next_index, peer_dumped_index):
            with self._lock:
                self.peer_next_index = peer_next_index
                self.peer_dumped_index = peer_dumped_index

        def get_peer_index(self):
            with self._lock:
                return self.peer_next_index, self.peer_dumped_index

        def set_peer_finished(self):
            with self._lock:
                self.peer_finished = True

        def is_peer_finished(self):
            with self._lock:
                return self.peer_finished

        def is_produce_finished(self):
            raise NotImplementedError("is_produce_finished is not Implemented "\
                                      "in base TransmitLeader ImplContext")

        def make_producer(self):
            raise NotImplementedError("make_producer is not Implemented "\
                                      "in base TransmitLeader ImplContext")

        def get_sync_content_by_next_index(self):
            raise NotImplementedError(
                    "get_sync_content_by_index is not Implemented "\
                    "in base TransmitLeader ImplContext"
                )

        def get_flying_item_cnt(self):
            raise NotImplementedError(
                    "get_flying_item is not Implemented "\
                    "in base TransmitLeader ImplContext"
                )

    def __init__(self, peer_client, master_client,
                 rank_id, kvstore, data_source, repr_str):
        self._lock = threading.Lock()
        self._peer_client = peer_client
        self._master_client = master_client
        self._rank_id = rank_id
        self._kvstore = kvstore
        self._data_source = data_source
        self._repr_str = repr_str
        self._partition_exhausted = False
        self._impl_ctx = None
        self._started = False
        self._worker_map = {}

    def start_routine_workers(self):
        with self._lock:
            if not self._started:
                self._worker_map = {
                    self._partition_allocator_name(): RoutineWorker(
                    self._partition_allocator_name(),
                    self._allocate_new_partition_fn,
                    self._allocate_new_partition_cond, 5),

                    self._producer_name(): RoutineWorker(
                    self._producer_name(),
                    self._data_producer_fn,
                    self._data_producer_cond, 5),

                    self._consumer_name(): RoutineWorker(
                    self._consumer_name(),
                    self._data_consumer_fn,
                    self._data_consumer_cond, 5),
                }
                for _, w in self._worker_map.items():
                    w.start_routine()
                self._started = True
                self._wakeup_new_partition_allocator()

    def stop_routine_workers(self):
        wait_join = True
        with self._lock:
            if self._started:
                wait_join = True
                self._started = False
        if wait_join:
            for w in self._worker_map.values():
                w.stop_routine()

    def _partition_allocator_name(self):
        return self._repr_str+'-new_partition_allocator'

    def _producer_name(self):
        return self._repr_str+'-data_producer'

    def _consumer_name(self):
        return self._repr_str+'-data_consumer'

    def _make_raw_data_request(self):
        raise NotImplementedError("_make_raw_data_request_for_process is "\
                                  "not implemented in base TransmitLeader")

    def _make_new_impl_ctx(self, raw_data_manifest):
        raise NotImplementedError("_make_new_impl_ctx is not "\
                                  "implemented in base TransmitLeader")

    def _wakeup_new_partition_allocator(self):
        self._worker_map[self._partition_allocator_name()].wakeup()

    @metrics.timer(func_name='allocate_new_partition_fn',
                   tags={'role': 'transmit_leader'})
    def _allocate_new_partition_fn(self):
        req = self._make_raw_data_request()
        rsp = self._master_client.RequestJoinPartition(req)
        if rsp.status.code != 0:
            raise RuntimeError("{} failed to call RequestJoinPartition, "\
                               "error msg {}".format(self._repr_str,
                                                     rsp.status.error_message))
        if rsp.HasField('finished'):
            self._set_partition_exhausted()
            return
        assert rsp.HasField('manifest'), "rsp of RequestJoinPartition must "\
                                         "has manifest if not finished tag"
        impl_ctx = self._make_new_impl_ctx(rsp.manifest)
        with self._lock:
            assert self._impl_ctx is None
            self._impl_ctx = impl_ctx
            self._wakeup_data_producer()
            self._wakeup_data_consumer()

    def _allocate_new_partition_cond(self):
        with self._lock:
            return self._impl_ctx is None and \
                    not self._partition_exhausted

    def _set_partition_exhausted(self):
        with self._lock:
            self._partition_exhausted = True

    def _wakeup_data_producer(self):
        self._worker_map[self._producer_name()].wakeup()

    def _process_producer_hook(self, impl_ctx):
        raise NotImplementedError("_process_producer_hook is not "\
                                  "implemented in base TransmitLeader")

    def _data_producer_fn(self, impl_ctx):
        assert isinstance(impl_ctx, TransmitLeader.ImplContext)
        if not impl_ctx.is_produce_finished():
            for item in impl_ctx.make_producer():
                if item is None:
                    continue
                self._wakeup_data_consumer()
                fly_item_cnt = impl_ctx.get_flying_item_cnt()
                if common.get_heap_mem_stats(None).CheckOomRisk(fly_item_cnt,
                                                                0.50):
                    logging.warning("%s early stop produce item since "\
                                    "oom risk", self._repr_str)
                    break

    def _data_producer_cond(self):
        with self._lock:
            oom_risk = False
            if self._impl_ctx is not None:
                self._process_producer_hook(self._impl_ctx)
                self._worker_map[self._producer_name()].setup_args(
                        self._impl_ctx
                    )
                fly_item_cnt = self._impl_ctx.get_flying_item_cnt()
                oom_risk = common.get_heap_mem_stats(None).CheckOomRisk(
                        fly_item_cnt, 0.60
                    )
            status = self._impl_ctx is not None and not oom_risk and \
                    not self._impl_ctx.is_produce_finished()
            logging.debug("%s producer condition return %s",
                          self.__class__.__name__, status)
            return status

    def _wakeup_data_consumer(self):
        self._worker_map[self._consumer_name()].wakeup()

    def _data_consumer_fn(self, impl_ctx):
        assert isinstance(impl_ctx, TransmitLeader.ImplContext)
        consume_finished = False
        if not impl_ctx.is_peer_finished():
            consume_finished = self._consume(impl_ctx)
        if consume_finished or impl_ctx.is_peer_finished():
            if self._finish_partition(impl_ctx):
                self._wakeup_new_partition_allocator()

    def _data_consumer_cond(self):
        with self._lock:
            if self._impl_ctx is not None:
                self._worker_map[self._consumer_name()].setup_args(
                        self._impl_ctx
                    )
            return self._impl_ctx is not None

    def _consume(self, impl_ctx):
        assert isinstance(impl_ctx, TransmitLeader.ImplContext)
        peer_finished = self._start_partition(impl_ctx)
        if peer_finished:
            impl_ctx.set_peer_finished()
        consume_finished = False
        while not impl_ctx.is_peer_finished():
            consume_finished, item = impl_ctx.get_sync_content_by_next_index()
            if item is None:
                break
            self._send_sync_content(impl_ctx, item)
        return consume_finished

    @metrics.timer(func_name='start_partition',
                   tags={'role': 'transmit_leader'})
    def _start_partition(self, impl_ctx):
        assert isinstance(impl_ctx, TransmitLeader.ImplContext)
        req = dj_pb.StartPartitionRequest(
            data_source_meta=self._data_source.data_source_meta,
            rank_id=self._rank_id,
            partition_id=impl_ctx.partition_id
        )
        rsp = self._peer_client.StartPartition(req)
        if rsp.status.code != 0:
            raise RuntimeError("{} failed to call for start partition {}, "\
                               "reason {}".format(self._repr_str,
                               impl_ctx.partition_id, rsp.status.error_message))
        self._update_peer_index(impl_ctx, rsp.next_index, rsp.dumped_index)
        return rsp.finished

    @metrics.timer(func_name='finish_partition',
                   tags={'role': 'transmit_leader'})
    def _send_sync_content(self, impl_ctx, item):
        assert isinstance(impl_ctx, TransmitLeader.ImplContext)
        req = dj_pb.SyncPartitionRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                sync_content=self._make_sync_content(item)
            )
        rsp = self._peer_client.SyncPartition(req)
        if rsp.status.code != 0:
            raise RuntimeError("Peer of {} refuse item. reason: {},".format(
                                self._repr_str, rsp.status.error_message))
        self._update_peer_index(impl_ctx, rsp.next_index, rsp.dumped_index)

    @metrics.timer(func_name='finish_partition',
                   tags={'role': 'transmit_leader'})
    def _finish_partition(self, impl_ctx):
        assert isinstance(impl_ctx, TransmitLeader.ImplContext)
        if not impl_ctx.is_peer_finished():
            req = dj_pb.FinishPartitionRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    rank_id=self._rank_id,
                    partition_id=impl_ctx.partition_id
                )
            rsp = self._peer_client.FinishPartition(req)
            if rsp.status.code != 0:
                raise RuntimeError(
                        "{} failed to call peer finish partition reason: " \
                        "{}".format(self._repr_str, rsp.status.error_message)
                    )
            if rsp.finished:
                impl_ctx.set_peer_finished()
        if not impl_ctx.is_peer_finished():
            logging.debug("peer of %s is still dumping item for partition "\
                          "%d waitiing", self._repr_str, impl_ctx.partition_id)
            return False

        logging.debug("peer of %s has dump all item for partition %d",
                      self._repr_str, impl_ctx.partition_id)
        req = self._make_finish_raw_data_request(impl_ctx)
        rsp = self._master_client.FinishJoinPartition(req)
        if rsp.code != 0:
            raise RuntimeError("{} failed to finish partition. reason: {}"\
                               .format(self._repr_str, rsp.error_message))
        logging.debug("%s has finished for partition %d",
                      self._repr_str, impl_ctx.partition_id)
        self._impl_ctx = None
        return True

    def _make_finish_raw_data_request(self, impl_ctx):
        raise NotImplementedError("_make_finish_raw_data_request is not "\
                                  "implemented in base TransmitLeader")

    def _make_sync_content(self, item):
        raise NotImplementedError("_make_sync_content is not "\
                                  "implemented in base TransmitLeader")

    @metrics.timer(func_name='update_peer_index',
                   tags={'role': 'transmit_leader'})
    def _update_peer_index(self, impl_ctx, peer_next_index, peer_dumped_index):
        assert isinstance(impl_ctx, TransmitLeader.ImplContext)
        _, dumped_index = impl_ctx.get_peer_index()
        impl_ctx.set_peer_index(peer_next_index, peer_dumped_index)
        if dumped_index < peer_dumped_index:
            req = dj_pb.RawDataRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    rank_id=self._rank_id,
                    partition_id=impl_ctx.partition_id,
                    peer_dumped_index=dj_pb.PeerDumpedIndex(
                            peer_dumped_index=peer_dumped_index
                        )
                )
            rsp = self._master_client.ForwardPeerDumpedIndex(req)
            if rsp.code != 0:
                raise RuntimeError("{} failed to forward peer dumped index "\
                                   "to {} reason: {}".format(self._repr_str,
                                                             peer_dumped_index,
                                                             rsp.error_message))
            metrics.emit_store('peer_dumped_index', peer_dumped_index,
                               self._get_metrics_tag(impl_ctx))

    def _get_metrics_tag(self, impl_ctx):
        assert isinstance(impl_ctx, TransmitLeader.ImplContext)
        ds_name = self._data_source.data_source_meta.name
        return {'data_source_name': ds_name,
                'partition': impl_ctx.partition_id,
                'role': 'transmit_leader'}

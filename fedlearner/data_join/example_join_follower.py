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

from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.data_block_dumper import DataBlockDumperManager

class ExampleJoinFollower(object):
    class ImplContext(object):
        def __init__(self, etcd, data_source,
                     partition_id, raw_data_options):
            self.data_block_dumper_manager = DataBlockDumperManager(
                    etcd, data_source, partition_id, raw_data_options
                )
            self.partition_id = partition_id

        def __getattr__(self, attr):
            return getattr(self.data_block_dumper_manager, attr)

    def __init__(self, etcd, data_source, raw_data_options):
        self._lock = threading.Lock()
        self._etcd = etcd
        self._data_source = data_source
        self._raw_data_options = raw_data_options
        self._data_block_dump_worker = None
        self._impl_ctx = None
        self._started = False

    def start_sync_partition(self, partition_id):
        with self._lock:
            if self._impl_ctx is not None and \
                    self._impl_ctx.partition_id != partition_id:
                raise RuntimeError(
                            "partition {} is not finished".format(
                                self._impl_ctx.partition_id)
                        )
            if self._impl_ctx is None:
                self._impl_ctx = ExampleJoinFollower.ImplContext(
                        self._etcd, self._data_source,
                        partition_id, self._raw_data_options
                    )
            return self._impl_ctx.get_next_data_block_index()

    def add_synced_item(self, req):
        assert req.HasField('data_block_meta'), \
            "the request must has data_block_meta for ExampleJoinFollower"
        with self._lock:
            self._check_status(req.data_block_meta.partition_id)
            return self._impl_ctx.add_synced_data_block_meta(
                    req.data_block_meta
                )

    def finish_sync_partition(self, partition_id):
        with self._lock:
            self._check_status(partition_id)
            self._impl_ctx.finish_sync_data_block_meta()
            return not self._impl_ctx.need_dump()

    def get_processing_partition_id(self):
        with self._lock:
            if self._impl_ctx is None:
                return None
            return self._impl_ctx.partition_id

    def reset_partition(self, partition_id):
        with self._lock:
            if not self._check_status(partition_id, False):
                return
            if not self._impl_ctx.is_synced_data_block_meta_finished() or \
                    self._impl_ctx.need_dump():
                raise RuntimeError("partition {} is dumpping data " \
                                   "block meta".format(partition_id))
            self._impl_ctx = None

    def start_dump_worker(self):
        with self._lock:
            if not self._started:
                assert self._data_block_dump_worker is None, \
                    "the data block dumper worker should be None "\
                    "if dumper worker is not started"
                self._data_block_dump_worker = RoutineWorker(
                        'data_block_dumper',
                        self._dump_data_block_fn,
                        self._dump_data_block_cond, 5
                    )
                self._data_block_dump_worker.start_routine()
                self._started = True

    def stop_dump_worker(self):
        dumper_worker = None
        with self._lock:
            if self._data_block_dump_worker is not None:
                dumper_worker = self._data_block_dump_worker
                self._data_block_dump_worker = None
        if dumper_worker is not None:
            dumper_worker.stop_routine()

    def _check_status(self, partition_id, raise_exception=True):
        if self._impl_ctx is None:
            if not raise_exception:
                return False
            raise RuntimeError("no partition is processing")
        if partition_id != self._impl_ctx.partition_id:
            if not raise_exception:
                return False
            raise RuntimeError(
                    "partition id mismatch {} != {}".format(
                        partition_id, self._impl_ctx.partition_id)
                )
        return True

    def _dump_data_block_fn(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleJoinFollower.ImplContext)
        with impl_ctx.make_data_block_dumper() as dumper:
            dumper()

    def _dump_data_block_cond(self):
        with self._lock:
            if self._impl_ctx is not None and self._impl_ctx.need_dump():
                self._data_block_dump_worker.setup_args(self._impl_ctx)
                return True
            return False

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
    def __init__(self, etcd, data_source, options):
        self._lock = threading.Lock()
        self._etcd = etcd
        self._data_source = data_source
        self._options = options
        self._data_block_dump_manager = None
        self._data_block_dump_worker = None
        self._started = False

    def start_create_data_block(self, partition_id):
        with self._lock:
            dump_manager = self._data_block_dump_manager
            if (dump_manager is not None and
                    dump_manager.get_partition_id() != partition_id):
                raise RuntimeError("partition {} is not finished".format(
                                   dump_manager.get_partition_id()))
            if dump_manager is None:
                self._data_block_dump_manager = DataBlockDumperManager(
                        self._etcd, self._data_source,
                        partition_id, self._options
                    )
                dump_manager = self._data_block_dump_manager
            next_index = dump_manager.get_next_data_block_index()
            return next_index

    def add_synced_data_block_meta(self, meta):
        with self._lock:
            self._check_status(meta.partition_id)
            manager = self._data_block_dump_manager
            return manager.append_synced_data_block_meta(meta)

    def finish_sync_data_block_meta(self, partition_id):
        with self._lock:
            self._check_status(partition_id)
            self._data_block_dump_manager.finish_sync_data_block_meta()
            return not self._data_block_dump_manager.need_dump()

    def get_processing_partition_id(self):
        with self._lock:
            if self._data_block_dump_manager is None:
                return None
            return self._data_block_dump_manager.get_partition_id()

    def reset_dump_partition(self):
        with self._lock:
            if self._data_block_dump_manager is None:
                return
            dump_manager = self._data_block_dump_manager
            partition_id = dump_manager.get_partition_id()
            self._check_status(partition_id)
            if (not dump_manager.data_block_meta_sync_finished() or
                    dump_manager.need_dump()):
                raise RuntimeError(
                        "partition {} is dumpping".format(partition_id)
                    )
            self._data_block_dump_manager = None

    def start_dump_worker(self):
        with self._lock:
            if not self._started:
                assert self._data_block_dump_worker is None
                self._data_block_dump_worker = RoutineWorker(
                        'data_block_dumper',
                        self._dump_data_block_fn,
                        self._dump_data_block_cond, 1
                    )
                self._data_block_dump_worker.start_routine()
                self._started = True

    def stop_dump_worker(self):
        dumper = None
        with self._lock:
            if self._data_block_dump_worker is not None:
                dumper = self._data_block_dump_worker
                self._data_block_dump_worker = None
        if dumper is not None:
            dumper.stop_routine()

    def _check_status(self, partition_id):
        if self._data_block_dump_manager is None:
            raise RuntimeError("no partition is processing")
        ptn_id = self._data_block_dump_manager.get_partition_id()
        if partition_id != ptn_id:
            raise RuntimeError("partition id mismatch {} != {}".format(
                                partition_id, ptn_id))

    def _dump_data_block_fn(self):
        dump_manager = self._data_block_dump_manager
        assert dump_manager is not None
        if dump_manager.need_dump():
            dump_manager.dump_data_blocks()

    def _dump_data_block_cond(self):
        with self._lock:
            return (self._data_block_dump_manager is not None and
                        self._data_block_dump_manager.need_dump())

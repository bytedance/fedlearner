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
from fedlearner.data_join.example_id_dumper import ExampleIdDumperManager

class ExampleIdSyncFollower(object):
    def __init__(self, data_source):
        self._lock = threading.Lock()
        self._data_source = data_source
        self._example_id_dump_manager = None
        self._example_id_dump_worker = None
        self._started = False

    def start_dump_partition(self, partition_id):
        with self._lock:
            if (self._example_id_dump_manager is not None and
                    self._example_id_dump_manager.get_partition_id() !=
                        partition_id):
                ptn_id = self._example_id_dump_manager.get_partition_id()
                raise RuntimeError("partition {} is not finished".format(
                                    ptn_id))
            if self._example_id_dump_manager is None:
                self._example_id_dump_manager = ExampleIdDumperManager(
                        self._data_source, partition_id)
            dump_manager = self._example_id_dump_manager
            next_index = dump_manager.get_next_index()
            return next_index

    def add_synced_example_req(self, synced_example_req):
        with self._lock:
            self._check_status(synced_example_req.partition_id)
            return self._example_id_dump_manager.append_synced_example_req(
                        synced_example_req)

    def finish_sync_partition_example(self, partition_id):
        with self._lock:
            self._check_status(partition_id)
            self._example_id_dump_manager.finish_sync_example()
            return not self._example_id_dump_manager.need_dump()

    def reset_dump_partition(self):
        with self._lock:
            if self._example_id_dump_manager is None:
                return
            partition_id = self._example_id_dump_manager.get_partition_id()
            self._check_status(partition_id)
            if (not self._example_id_dump_manager.example_sync_finished() or
                    self._example_id_dump_manager.need_dump()):
                raise RuntimeError(
                        "partition {} is dumpping".format(partition_id)
                    )
            self._example_id_dump_manager = None

    def get_processing_partition_id(self):
        with self._lock:
            if self._example_id_dump_manager is None:
                return None
            return self._example_id_dump_manager.get_partition_id()

    def start_dump_worker(self):
        with self._lock:
            if not self._started:
                assert self._example_id_dump_worker is None
                self._example_id_dump_worker = RoutineWorker(
                        'example_id_dumper',
                        self._dump_example_ids_fn,
                        self._dump_example_ids_cond, 1
                    )
                self._example_id_dump_worker.start_routine()
                self._started = True

    def stop_dump_worker(self):
        dumper = None
        with self._lock:
            if self._example_id_dump_worker is not None:
                dumper = self._example_id_dump_worker
                self._dump_worker = None
        if dumper is not None:
            dumper.stop_routine()

    def _check_status(self, partition_id):
        if self._example_id_dump_manager is None:
            raise RuntimeError("no partition is processing")
        ptn_id = self._example_id_dump_manager.get_partition_id()
        if partition_id != ptn_id:
            raise RuntimeError("partition id mismatch {} != {}".format(
                                partition_id, ptn_id))

    def _dump_example_ids_fn(self):
        dump_manager = None
        with self._lock:
            dump_manager = self._example_id_dump_manager
        assert dump_manager is not None
        if dump_manager.need_dump():
            dump_manager.dump_example_ids()

    def _dump_example_ids_cond(self):
        with self._lock:
            return (self._example_id_dump_manager is not None and
                    self._example_id_dump_manager.need_dump())

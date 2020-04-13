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

class TransmitFollower(object):
    class ImplContext(object):
        def __init__(self, partition_id):
            self.partition_id = partition_id

        def get_next_index(self):
            raise NotImplementedError("get_next_index is not Implemented "\
                                      "in base ImplContext")

        def get_dumped_index(self):
            raise NotImplementedError("get_dumped_index is not Implemented "\
                                      "in base ImplContext")

        def add_synced_content(self, sync_ctnt):
            raise NotImplementedError("add_synced_content is not Implemented "\
                                      "in base ImplContext")

        def finish_sync_content(self):
            raise NotImplementedError("finish_sync_content is not Implemented "\
                                      "in base ImplContext")

        def need_dump(self):
            raise NotImplementedError("need_dump is not Implemented "\
                                      "in base ImplContext")

        def make_dumper(self):
            raise NotImplementedError("make_dumper is not Implemented "\
                                      "in base ImplContext")

        def is_sync_content_finished(self):
            raise NotImplementedError("is_sync_content_finished is not "\
                                      "Implemented in base ImplContext")

    def __init__(self, etcd, data_source, repr_str):
        self._lock = threading.Lock()
        self._etcd = etcd
        self._data_source = data_source
        self._repr_str = repr_str
        self._dump_worker = None
        self._impl_ctx = None
        self._started = False

    def start_sync_partition(self, partition_id):
        with self._lock:
            if self._impl_ctx is not None and \
                    self._impl_ctx.partition_id != partition_id:
                raise RuntimeError(
                        "{} is processing partition {}".format(
                            self._repr_str, self._impl_ctx.partition_id
                        )
                    )
            if self._impl_ctx is None:
                self._impl_ctx = self._make_new_impl_ctx(partition_id)
            return self._impl_ctx.get_next_index(), \
                    self._impl_ctx.get_dumped_index()

    def add_synced_item(self, sync_ctnt):
        with self._lock:
            partition_id = \
                self._extract_partition_id_from_sync_content(sync_ctnt)
            self._check_status(partition_id)
            filled, next_index = self._impl_ctx.add_synced_content(sync_ctnt)
            if filled:
                self._dump_worker.wakeup()
            return filled, next_index, self._impl_ctx.get_dumped_index()

    def finish_sync_partition(self, partition_id):
        with self._lock:
            self._check_status(partition_id)
            self._impl_ctx.finish_sync_content()
            return not self._impl_ctx.need_dump(), \
                    self._impl_ctx.get_dumped_index()

    def reset_partition(self, partition_id):
        with self._lock:
            if not self._check_status(partition_id, False):
                return
            if not self._impl_ctx.is_sync_content_finished() or \
                    self._impl_ctx.need_dump():
                raise RuntimeError("{} is still dumping for partition {}"\
                                   .format(self._repr_str, partition_id))
            self._impl_ctx = None

    def get_processing_partition_id(self):
        with self._lock:
            if self._impl_ctx is None:
                return None
            return self._impl_ctx.partition_id

    def start_dump_worker(self):
        with self._lock:
            if not self._started:
                assert self._dump_worker is None, \
                    "dumper woker for {} should be None if "\
                    "not started".format(self._repr_str)
                self._dump_worker = RoutineWorker(
                        self._repr_str+'-dump_worker',
                        self._dump_fn, self._dump_cond, 1
                    )
                self._dump_worker.start_routine()
                self._started = True

    def stop_dump_worker(self):
        dumper_worker = None
        with self._lock:
            dumper_worker = self._dump_worker
            self._dump_worker = None
        if dumper_worker is not None:
            dumper_worker.stop_routine()

    def _check_status(self, partition_id, raise_exception=True):
        if self._impl_ctx is None:
            if not raise_exception:
                return False
            raise RuntimeError("no partition is processing")
        if self._impl_ctx.partition_id != partition_id:
            if not raise_exception:
                return False
            raise RuntimeError(
                    "partition id mismatch {} != {} for {}".format(
                        self._impl_ctx.partition_id,
                        partition_id, self._repr_str
                    )
                )
        return True

    def _dump_fn(self, impl_ctx):
        with impl_ctx.make_dumper() as dumper:
            dumper()

    def _dump_cond(self):
        with self._lock:
            if self._impl_ctx is not None and self._impl_ctx.need_dump():
                self._dump_worker.setup_args(self._impl_ctx)
                return True
            return False

    def _make_new_impl_ctx(self, partition_id):
        raise NotImplementedError("_make_new_impl_ctx is not Implemented "\
                                  "in base TransmitFollower")

    def _extract_partition_id_from_sync_content(self, sync_content):
        raise NotImplementedError("_extract_partition_id_from_sync_content "\
                                  "is not Implemented in base TransmitFollower")

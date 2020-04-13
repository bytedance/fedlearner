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

from fedlearner.data_join.example_id_dumper import ExampleIdDumperManager
from fedlearner.data_join.transmit_follower import TransmitFollower

class ExampleIdSyncFollower(TransmitFollower):
    class ImplContext(TransmitFollower.ImplContext):
        def __init__(self, etcd, data_source,
                     partition_id, example_id_dump_options):
            super(ExampleIdSyncFollower.ImplContext, self).__init__(
                    partition_id
                )
            self.example_id_dumper_manager = \
                    ExampleIdDumperManager(etcd, data_source,
                                           partition_id,
                                           example_id_dump_options)

        def get_next_index(self):
            return self.example_id_dumper_manager.get_next_index()

        def get_dumped_index(self):
            return self.example_id_dumper_manager.get_dumped_index()

        def add_synced_content(self, sync_ctnt):
            return self.example_id_dumper_manager.add_example_id_batch(
                    sync_ctnt.lite_example_ids
                )

        def finish_sync_content(self):
            self.example_id_dumper_manager.finish_sync_example_id()

        def need_dump(self):
            return self.example_id_dumper_manager.need_dump()

        def make_dumper(self):
            return self.example_id_dumper_manager.make_example_id_dumper()

        def is_sync_content_finished(self):
            return self.example_id_dumper_manager.is_sync_example_id_finished()

    def __init__(self, etcd, data_source, example_id_dump_options):
        super(ExampleIdSyncFollower, self).__init__(etcd, data_source,
                                                    'example_id_sync_follower')
        self._example_id_dump_options = example_id_dump_options

    def _make_new_impl_ctx(self, partition_id):
        return ExampleIdSyncFollower.ImplContext(
                self._etcd, self._data_source,
                partition_id, self._example_id_dump_options
            )

    def _extract_partition_id_from_sync_content(self, sync_ctnt):
        assert sync_ctnt.HasField('lite_example_ids'), \
            "sync content should has lite_example_ids for ExampleIdSyncFollower"
        return sync_ctnt.lite_example_ids.partition_id

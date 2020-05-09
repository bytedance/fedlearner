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

from fedlearner.data_join.data_block_dumper import DataBlockDumperManager
from fedlearner.data_join.transmit_follower import TransmitFollower

class ExampleJoinFollower(TransmitFollower):
    class ImplContext(TransmitFollower.ImplContext):
        def __init__(self, etcd, data_source, partition_id,
                     raw_data_options, data_block_builder_options):
            super(ExampleJoinFollower.ImplContext, self).__init__(partition_id)
            self.data_block_dumper_manager = DataBlockDumperManager(
                    etcd, data_source, partition_id,
                    raw_data_options, data_block_builder_options
                )

        def get_next_index(self):
            return self.data_block_dumper_manager.get_next_data_block_index()

        def get_dumped_index(self):
            return self.data_block_dumper_manager.get_dumped_data_block_index()

        def add_synced_content(self, sync_ctnt):
            return self.data_block_dumper_manager.add_synced_data_block_meta(
                    sync_ctnt.data_block_meta
                )

        def finish_sync_content(self):
            self.data_block_dumper_manager.finish_sync_data_block_meta()

        def need_dump(self):
            return self.data_block_dumper_manager.need_dump()

        def make_dumper(self):
            return self.data_block_dumper_manager.make_data_block_dumper()

        def is_sync_content_finished(self):
            dumper_manager = self.data_block_dumper_manager
            return dumper_manager.is_synced_data_block_meta_finished()

    def __init__(self, etcd, data_source,
                 raw_data_options, data_block_builder_options):
        super(ExampleJoinFollower, self).__init__(etcd, data_source,
                                                  'example_join_follower')
        self._raw_data_options = raw_data_options
        self._data_block_builder_options = data_block_builder_options

    def _make_new_impl_ctx(self, partition_id):
        return ExampleJoinFollower.ImplContext(
                self._etcd, self._data_source, partition_id,
                self._raw_data_options, self._data_block_builder_options
            )

    def _extract_partition_id_from_sync_content(self, sync_ctnt):
        assert sync_ctnt.HasField('data_block_meta'), \
            "sync content should has data_block_meta for ExampleJoinFollower"
        return sync_ctnt.data_block_meta.partition_id

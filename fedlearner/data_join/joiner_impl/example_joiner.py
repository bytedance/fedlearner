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

from fedlearner.data_join.raw_data_visitor import RawDataVisitor
from fedlearner.data_join.example_id_visitor import (
    ExampleIdManager, ExampleIdVisitor
)
from fedlearner.data_join.data_block_manager import (
    DataBlockBuilder, DataBlockManager
)

class ExampleJoiner(object):
    def __init__(self, etcd, data_source, partition_id, options):
        self._data_source = data_source
        self._partition_id = partition_id
        self._leader_visitor = ExampleIdVisitor(
                ExampleIdManager(data_source, partition_id)
            )
        self._follower_visitor = RawDataVisitor(
                etcd, data_source, partition_id, options
            )
        self._data_block_manager = DataBlockManager(data_source, partition_id)

        self._data_block_builder = None
        self._stale_with_dfs = False
        self._follower_restart_index = 0
        self._sync_state()

    def join_example(self):
        raise NotImplementedError(
                "join exampel not implement for base class: %s" %
                ExampleJoiner.name()
            )

    @classmethod
    def name(cls):
        return 'EXAMPLE_JOINER'

    def get_data_block_number(self):
        return self._data_block_manager.num_dumped_data_block()

    def get_data_block_meta(self, index):
        return self._data_block_manager.get_data_block_meta_by_index(index)

    def join_finished(self):
        return self._data_block_manager.join_finished()

    def _sync_state(self):
        meta = self._data_block_manager.get_last_data_block_meta(
                self._stale_with_dfs
            )
        if meta is not None:
            try:
                self._leader_visitor.seek(meta.leader_end_index)
            except StopIteration:
                logging.warning("leader visitor finished")
            try:
                self._follower_visitor.seek(meta.follower_restart_index)
            except StopIteration:
                logging.warning("follower visitor finished")
            if (self._leader_visitor.finished() or
                    self._follower_visitor.finished()):
                self._data_block_manager.finish_join()
        self._stale_with_dfs = False

    def _get_data_block_builder(self):
        if self._data_block_builder is not None:
            return self._data_block_builder
        data_block_index = self._data_block_manager.get_dumped_data_block_num()
        self._data_block_builder = DataBlockBuilder(
                self._data_source.data_block_dir,
                self._partition_id,
                data_block_index,
                self._data_source.data_source_meta.max_example_in_data_block
            )
        return self._data_block_builder

    def _finish_data_block(self):
        assert self._data_block_builder is not None
        self._data_block_builder.set_follower_restart_index(
            self._follower_restart_index)
        self._data_block_builder.finish_data_block()
        meta = self._data_block_builder.get_data_block_meta()
        if meta is not None:
            self._data_block_manager.add_dumped_data_block_meta(meta)
        self._data_block_builder = None

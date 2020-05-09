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

from fedlearner.data_join.joiner_impl.example_joiner import ExampleJoiner

class SortRunExampleJoiner(ExampleJoiner):
    @classmethod
    def name(cls):
        return 'SORT_RUN_JOINER'

    def _inner_joiner(self, state_stale):
        if self.is_join_finished():
            return
        sync_example_id_finished, raw_data_finished = \
                self._prepare_join(state_stale)
        for fi, li, fe in self._make_joined_generator():
            builder = self._get_data_block_builder(True)
            assert builder is not None
            builder.append_item(fe, fe.example_id, 0, li, fi)
            if builder.check_data_block_full():
                self._follower_restart_index = fi
                yield self._finish_data_block()
        join_data_finished = sync_example_id_finished and raw_data_finished
        if self._get_data_block_builder(False) is not None and \
                (self._need_finish_data_block_since_interval() or
                    join_data_finished):
            self._follower_restart_index = self._follower_visitor.get_index()
            yield self._finish_data_block()
        if join_data_finished:
            self._set_join_finished()
            logging.warning("finish join example for partition %d by %s",
                            self._partition_id, self.name())

    def _make_joined_generator(self):
        while self._forward_visitor():
            if not self._follower_visitor.started():
                continue
            li, le = self._leader_visitor.get_index(), \
                        self._leader_visitor.get_item()
            fi, fe = self._follower_visitor.get_index(), \
                        self._follower_visitor.get_item()
            if le.example_id == fe.example_id:
                yield fi, li, fe

    @classmethod
    def _forward_one_step(cls, visitor):
        for _, item in visitor:
            return True
        assert visitor.finished()
        return False

    def _forward_visitor(self):
        leader_item = None if not self._leader_visitor.started() \
                        else self._leader_visitor.get_item()
        follower_item = None if not self._follower_visitor.started() \
                        else self._follower_visitor.get_item()
        if leader_item is None or \
                (follower_item is not None and
                    leader_item.example_id <= follower_item.example_id):
            return self._forward_one_step(self._leader_visitor)
        return self._forward_one_step(self._follower_visitor)

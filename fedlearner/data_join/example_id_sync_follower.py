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
import bisect
import logging
import os
from collections import OrderedDict

import tensorflow.compat.v1 as tf
from dateutil import parser as date_parser

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import metrics
from fedlearner.data_join.common import partition_repr, make_tf_record_iter, \
    convert_to_iso_format
from fedlearner.data_join.example_id_dumper import ExampleIdDumperManager
from fedlearner.data_join.transmit_follower import TransmitFollower


class ExampleIdSyncFollower(TransmitFollower):
    class ImplContext(TransmitFollower.ImplContext):
        def __init__(self, kvstore, data_source,
                     partition_id, example_id_dump_options):
            super(ExampleIdSyncFollower.ImplContext, self).__init__(
                    partition_id
                )
            self.example_id_dumper_manager = \
                    ExampleIdDumperManager(kvstore, data_source,
                                           partition_id,
                                           example_id_dump_options)

        def get_next_index(self):
            return self.example_id_dumper_manager.get_next_index()

        def get_dumped_index(self):
            return self.example_id_dumper_manager.get_dumped_index()

        def add_synced_content(self, sync_ctnt):
            return self.example_id_dumper_manager.add_example_id_batch(
                    sync_ctnt.packed_lite_example_ids
                )

        def finish_sync_content(self):
            self.example_id_dumper_manager.finish_sync_example_id()

        def need_dump(self):
            return self.example_id_dumper_manager.need_dump()

        def make_dumper(self):
            return self.example_id_dumper_manager.make_example_id_dumper()

        def is_sync_content_finished(self):
            return self.example_id_dumper_manager.is_sync_example_id_finished()

    def __init__(self, kvstore, data_source, example_id_dump_options):
        super(ExampleIdSyncFollower, self).__init__(kvstore, data_source,
                                                    'example_id_sync_follower')
        self._example_id_dump_options = example_id_dump_options

    @metrics.timer(func_name='make_new_impl_ctx',
                   tags={'role': 'transmit_follower'})
    def _make_new_impl_ctx(self, partition_id):
        return ExampleIdSyncFollower.ImplContext(
                self._kvstore, self._data_source,
                partition_id, self._example_id_dump_options
            )

    def _extract_partition_id_from_sync_content(self, sync_ctnt):
        assert sync_ctnt.HasField('packed_lite_example_ids'), \
            "sync content should has packed_lite_example_ids "\
            "for ExampleIdSyncFollower"
        return sync_ctnt.packed_lite_example_ids.partition_id

    def _rollback_partition(self, partition_id, rollback):
        """
        Args:
            partition_id: partition id of current impl_ctx
            rollback: rollback checkpoint timestamp

        Returns:
        Delete all example id file containing or older than `rollback`
        """
        if rollback <= 0:
            return
        partition_dir = os.path.join(self._data_source.output_base_dir,
                                     'example_dump',
                                     partition_repr(partition_id))
        partition_files = tf.io.gfile.ListDirectory(partition_dir)
        file_time = OrderedDict()
        last_file_timestamp = 0
        for file in partition_files:
            # extract the first event time of every file
            with make_tf_record_iter(file) as tfr_iter:
                oldest = next(tfr_iter)
                lite_example_ids = dj_pb.LiteExampleIds()
                lite_example_ids.ParseFromString(oldest)
                if len(lite_example_ids.event_time) > 0:
                    file_time[file] = date_parser.parse(
                        convert_to_iso_format(lite_example_ids.event_time[0])
                    ).timestamp()
                    last_file_timestamp = file_time[file]
                else:
                    file_time[file] = last_file_timestamp
        file_list = list(file_time.keys())
        time_list = list(file_time.values())
        rollback_point = bisect.bisect_left(time_list, rollback)
        # if the right side has a greater timestamp, than the rollback timestamp
        # is contained in the left side, hence the left side needs to be deleted
        if time_list[rollback_point] > rollback and rollback_point > 0:
            rollback_point -= 1
        retain = set(file_list[:rollback_point])
        for file in partition_files:
            if file not in retain:
                file_dir = os.path.join(partition_dir, file)
                tf.io.gfile.Remove(file_dir)
                logging.info('ROLLBACK: deleted example id file %s.', file_dir)

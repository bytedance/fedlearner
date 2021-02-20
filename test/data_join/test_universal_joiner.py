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

import unittest
import os
import random
import logging

import tensorflow.compat.v1 as tf
tf.enable_eager_execution()
import tensorflow_io
from tensorflow.compat.v1 import gfile
from google.protobuf import timestamp_pb2

from fedlearner.common import mysql_client
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join.common import interval_to_timestamp

from fedlearner.data_join import (
    data_block_manager, common, data_block_dumper,
    raw_data_manifest_manager, joiner_impl,
    example_id_dumper, raw_data_visitor, visitor
)
from fedlearner.data_join.data_block_manager import DataBlockBuilder
from fedlearner.data_join.raw_data_iter_impl.tf_record_iter import TfExampleItem

import datasource_producer as dsp

class TestUniversalJoin(dsp.DataSourceProducer):
    def setUp(self):
        self.init("test_uni_joiner", "invalid joiner as placeholder")

    #@unittest.skip("test")
    def test_attribution_join(self):
        self.example_joiner_options = dj_pb.ExampleJoinerOptions(
                  example_joiner='ATTRIBUTION_JOINER',
                  min_matching_window=32,
                  max_matching_window=51200,
                  max_conversion_delay=interval_to_timestamp("124"),
                  enable_negative_example_generator=True,
                  data_block_dump_interval=32,
                  data_block_dump_threshold=128,
                  negative_sampling_rate=0.8,
              )

        sei = joiner_impl.create_example_joiner(
                self.example_joiner_options,
                self.raw_data_options,
                dj_pb.WriterOptions(output_writer='TF_RECORD'),
                self.kvstore, self.data_source, 0
            )
        self.run_join(sei)

    #@unittest.skip("test2")
    def test_universal_join(self):
        self.example_joiner_options = dj_pb.ExampleJoinerOptions(
                  example_joiner='UNIVERSAL_JOINER',
                  min_matching_window=32,
                  max_matching_window=51200,
                  max_conversion_delay=interval_to_timestamp("124"),
                  enable_negative_example_generator=True,
                  data_block_dump_interval=32,
                  data_block_dump_threshold=128,
                  negative_sampling_rate=0.8,
                  join_expr="(id_type, example_id)",
                  join_key_mapper="DEFAULT",
              )
        self.version = dsp.Version.V2

        sei = joiner_impl.create_example_joiner(
                self.example_joiner_options,
                self.raw_data_options,
                dj_pb.WriterOptions(output_writer='TF_RECORD'),
                self.kvstore, self.data_source, 0
            )
        self.run_join(sei)

    #@unittest.skip("test3")
    def test_universal_join_attribution(self):
        self.example_joiner_options = dj_pb.ExampleJoinerOptions(
                  example_joiner='UNIVERSAL_JOINER',
                  min_matching_window=32,
                  max_matching_window=51200,
                  max_conversion_delay=interval_to_timestamp("124"),
                  enable_negative_example_generator=True,
                  data_block_dump_interval=32,
                  data_block_dump_threshold=128,
                  negative_sampling_rate=0.8,
                  join_expr="example_id or lt(event_time)",
                  join_key_mapper="DEFAULT",
              )
        self.version = dsp.Version.V2

        sei = joiner_impl.create_example_joiner(
                self.example_joiner_options,
                self.raw_data_options,
                dj_pb.WriterOptions(output_writer='TF_RECORD'),
                self.kvstore, self.data_source, 0
            )
        self.run_join(sei)

    def test_universal_join_key_mapper(self):
        mapper_code = """
from fedlearner.data_join.key_mapper.key_mapping import BaseKeyMapper
class TestKeyMapper(BaseKeyMapper):
    def leader_mapping(self, item) -> dict:
        res = item.click_id.split("_")
        return dict({"req_id":res[0], "cid":res[1]})

    def follower_mapping(self, item) -> dict:
        return dict()

    @classmethod
    def name(cls):
        return "TEST_MAPPER"
"""
        abspath = os.path.dirname(os.path.abspath(__file__))
        fname = "%s/../../fedlearner/data_join/key_mapper/impl/keymapper_mock.py"%abspath
        with open(fname, "w") as f:
            f.write(mapper_code)

        self.example_joiner_options = dj_pb.ExampleJoinerOptions(
                  example_joiner='UNIVERSAL_JOINER',
                  min_matching_window=32,
                  max_matching_window=51200,
                  max_conversion_delay=interval_to_timestamp("0"),
                  enable_negative_example_generator=True,
                  data_block_dump_interval=32,
                  data_block_dump_threshold=128,
                  negative_sampling_rate=0.8,
                  join_expr="(cid,req_id)",
                  join_key_mapper="TEST_MAPPER"
              )
        self.version = dsp.Version.V2

        sei = joiner_impl.create_example_joiner(
                self.example_joiner_options,
                self.raw_data_options,
                dj_pb.WriterOptions(output_writer='TF_RECORD'),
                self.kvstore, self.data_source, 0
            )
        self.run_join(sei)

        os.remove(fname)


    def run_join(self, sei):
        metas = []
        with sei.make_example_joiner() as joiner:
            for meta in joiner:
                metas.append(meta)
        self.assertEqual(len(metas), 0)
        self.generate_raw_data(0, 2 * 2048)
        dumper = example_id_dumper.ExampleIdDumperManager(
                self.kvstore, self.data_source, 0, self.example_id_dump_options
            )
        self.generate_example_id(dumper, 0, 3 * 2048)
        with sei.make_example_joiner() as joiner:
            for meta in joiner:
                metas.append(meta)
        self.generate_raw_data(2 * 2048, 2048)
        self.generate_example_id(dumper, 3 * 2048, 3 * 2048)
        with sei.make_example_joiner() as joiner:
            for meta in joiner:
                metas.append(meta)
        self.generate_raw_data(3 * 2048, 5 * 2048)
        self.generate_example_id(dumper, 6 * 2048, 2048)
        with sei.make_example_joiner() as joiner:
            for meta in joiner:
                metas.append(meta)
        self.generate_raw_data(8 * 2048, 2 * 2048)
        with sei.make_example_joiner() as joiner:
            for meta in joiner:
                metas.append(meta)
        self.generate_example_id(dumper, 7 * 2048, 3 * 2048)
        with sei.make_example_joiner() as joiner:
            for meta in joiner:
                metas.append(meta)
        sei.set_sync_example_id_finished()
        sei.set_raw_data_finished()
        with sei.make_example_joiner() as joiner:
            for meta in joiner:
                metas.append(meta)

        dbm = data_block_manager.DataBlockManager(self.data_source, 0)
        data_block_num = dbm.get_dumped_data_block_count()
        self.assertEqual(len(metas), data_block_num)
        join_count = 0
        for data_block_index in range(data_block_num):
            meta = dbm.get_data_block_meta_by_index(data_block_index)
            self.assertEqual(meta, metas[data_block_index])
            join_count += len(meta.example_ids)

        print("join rate {}/{}({}), min_matching_window {}, "\
              "max_matching_window {}".format(
              join_count, 20480 * 2,
              (join_count+.0)/(10 * 2048 * 2),
              self.example_joiner_options.min_matching_window,
              self.example_joiner_options.max_matching_window))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()

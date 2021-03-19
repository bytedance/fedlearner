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

import tensorflow.compat.v1 as tf
tf.enable_eager_execution()
import tensorflow_io
from tensorflow.compat.v1 import gfile
from google.protobuf import timestamp_pb2

from fedlearner.common import db_client
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join import (
    data_block_manager, common, data_block_dumper,
    raw_data_manifest_manager, joiner_impl,
    example_id_dumper, raw_data_visitor, visitor
)
from fedlearner.data_join.data_block_manager import DataBlockBuilder
from fedlearner.data_join.raw_data_iter_impl.tf_record_iter import TfExampleItem

class TestExampleJoin(unittest.TestCase):
    def setUp(self):
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = "milestone-f"
        data_source.data_source_meta.partition_num = 1
        data_source.output_base_dir = "./ds_output"
        self.raw_data_dir = "./raw_data"
        self.data_source = data_source
        self.raw_data_options = dj_pb.RawDataOptions(
                raw_data_iter='TF_RECORD',
                compressed_type='',
                optional_fields=['label']
            )
        self.example_id_dump_options = dj_pb.ExampleIdDumpOptions(
                example_id_dump_interval=1,
                example_id_dump_threshold=1024
            )
        self.example_joiner_options = dj_pb.ExampleJoinerOptions(
                example_joiner='STREAM_JOINER',
                min_matching_window=32,
                max_matching_window=128,
                data_block_dump_interval=30,
                data_block_dump_threshold=128
            )
        if gfile.Exists(self.data_source.output_base_dir):
            gfile.DeleteRecursively(self.data_source.output_base_dir)
        if gfile.Exists(self.raw_data_dir):
            gfile.DeleteRecursively(self.raw_data_dir)
        self.kvstore = db_client.DBClient('etcd', True)
        self.kvstore.delete_prefix(common.data_source_kvstore_base_dir(self.data_source.data_source_meta.name))
        self.total_raw_data_count = 0
        self.total_example_id_count = 0
        self.manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
            self.kvstore, self.data_source)
        self.g_data_block_index = 0

    def generate_raw_data(self, begin_index, item_count):
        raw_data_dir = os.path.join(self.raw_data_dir, common.partition_repr(0))
        if not gfile.Exists(raw_data_dir):
            gfile.MakeDirs(raw_data_dir)
        self.total_raw_data_count += item_count
        useless_index = 0
        rdm = raw_data_visitor.RawDataManager(self.kvstore, self.data_source, 0)
        fpaths = []
        for block_index in range(0, item_count // 2048):
            builder = DataBlockBuilder(
                    self.raw_data_dir,
                    self.data_source.data_source_meta.name,
                    0, block_index, dj_pb.WriterOptions(output_writer='TF_RECORD'), None
                )
            cands = list(range(begin_index + block_index * 2048,
                begin_index + (block_index + 1) * 2048))
            start_index = cands[0]
            for i in range(len(cands)):
                if random.randint(1, 4) > 2:
                    continue
                a = random.randint(i - 32, i + 32)
                b = random.randint(i - 32, i + 32)
                if a < 0:
                    a = 0
                if a >= len(cands):
                    a = len(cands) - 1
                if b < 0:
                    b = 0
                if b >= len(cands):
                    b = len(cands) - 1
                if (abs(cands[a]-i-start_index) <= 32 and
                        abs(cands[b]-i-start_index) <= 32):
                    cands[a], cands[b] = cands[b], cands[a]
            for example_idx in cands:
                feat = {}
                example_id = '{}'.format(example_idx).encode()
                feat['example_id'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[example_id]))
                event_time = 150000000 + example_idx
                feat['event_time'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[event_time]))
                label = random.choice([1, 0])
                if random.random() < 0.8:
                    feat['label'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[label]))
                example = tf.train.Example(features=tf.train.Features(feature=feat))
                builder.append_item(TfExampleItem(example.SerializeToString()),
                                    useless_index, useless_index)
                useless_index += 1
            meta = builder.finish_data_block()
            fname = common.encode_data_block_fname(
                    self.data_source.data_source_meta.name, meta
                )
            fpath = os.path.join(raw_data_dir, fname)
            fpaths.append(dj_pb.RawDataMeta(file_path=fpath,
                                            timestamp=timestamp_pb2.Timestamp(seconds=3)))
            self.g_data_block_index += 1
        all_files = [os.path.join(raw_data_dir, f)
                    for f in gfile.ListDirectory(raw_data_dir)
                    if not gfile.IsDirectory(os.path.join(raw_data_dir, f))]
        for fpath in all_files:
            if not fpath.endswith(common.DataBlockSuffix):
                gfile.Remove(fpath)
        self.manifest_manager.add_raw_data(0, fpaths, False)

    def generate_example_id(self, dumper, start_index, item_count):
        self.total_example_id_count += item_count
        for req_index in range(start_index // 512, self.total_example_id_count // 512):
            cands = list(range(req_index * 512, (req_index + 1) * 512))
            start_index = cands[0]
            for i in range(len(cands)):
                if random.randint(1, 4) > 1:
                    continue
                a = random.randint(i - 64, i + 64)
                b = random.randint(i - 64, i + 64)
                if a < 0:
                    a = 0
                if a >= len(cands):
                    a = len(cands) - 1
                if b < 0:
                    b = 0
                if b >= len(cands):
                    b = len(cands) - 1
                if (abs(cands[a]-i-start_index) <= 64 and
                        abs(cands[b]-i-start_index) <= 64):
                    cands[a], cands[b] = cands[b], cands[a]
            example_id_list = []
            event_time_list = []
            for example_idx in cands:
                example_id_list.append('{}'.format(example_idx).encode())
                event_time_list.append(150000000 + example_idx)
            tf_example_id = tf.train.Feature(bytes_list=tf.train.BytesList(value=example_id_list))
            tf_event_time = tf.train.Feature(int64_list=tf.train.Int64List(value=event_time_list))

            example_id_batch = dj_pb.LiteExampleIds(
                    partition_id=0,
                    begin_index=req_index * 512,
                    features=tf.train.Features(feature={'example_id': tf_example_id, 'event_time': tf_event_time})
                )
            packed_example_id_batch = dj_pb.PackedLiteExampleIds(
                    partition_id=0,
                    begin_index=req_index*512,
                    example_id_num=len(cands),
                    sered_lite_example_ids=example_id_batch.SerializeToString()
                )
            dumper.add_example_id_batch(packed_example_id_batch)
            self.assertEqual(dumper.get_next_index(), (req_index + 1) * 512)
        self.assertTrue(dumper.need_dump())
        with dumper.make_example_id_dumper() as eid:
            eid()

    def test_example_joiner(self):
        sei = joiner_impl.create_example_joiner(
                self.example_joiner_options,
                self.raw_data_options,
                dj_pb.WriterOptions(output_writer='TF_RECORD'),
                self.kvstore, self.data_source, 0
            )
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
              join_count, 20480,
              (join_count+.0)/(10 * 2048),
              self.example_joiner_options.min_matching_window,
              self.example_joiner_options.max_matching_window))

    def tearDown(self):
        if gfile.Exists(self.data_source.output_base_dir):
            gfile.DeleteRecursively(self.data_source.output_base_dir)
        if gfile.Exists(self.raw_data_dir):
            gfile.DeleteRecursively(self.raw_data_dir)
        self.kvstore.delete_prefix(common.data_source_kvstore_base_dir(self.data_source.data_source_meta.name))

if __name__ == '__main__':
    unittest.main()

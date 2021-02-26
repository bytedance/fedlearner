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
import enum

import tensorflow.compat.v1 as tf
tf.enable_eager_execution()
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

class Version:
    V1 = 1
    V2 = 2

class DataSourceProducer(unittest.TestCase):
    def init(self, dsname, joiner_name, version=Version.V1):
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = dsname
        data_source.data_source_meta.partition_num = 1
        data_source.output_base_dir = "%s_ds_output" % dsname
        self.raw_data_dir = "%s_raw_data" % dsname
        self.data_source = data_source
        self.raw_data_options = dj_pb.RawDataOptions(
                raw_data_iter='TF_RECORD',
                compressed_type='',
                #optional_fields = [], #FIXME
            )
        self.example_id_dump_options = dj_pb.ExampleIdDumpOptions(
                example_id_dump_interval=1,
                example_id_dump_threshold=1024
            )
        self.example_joiner_options = dj_pb.ExampleJoinerOptions(
                example_joiner=joiner_name,
                min_matching_window=32,
                max_matching_window=51200,
                max_conversion_delay=interval_to_timestamp("124"),
                enable_negative_example_generator=True,
                data_block_dump_interval=32,
                data_block_dump_threshold=128,
                negative_sampling_rate=0.8,
                join_expr="example_id",
                join_key_mapper="DEFAULT",
            )
        if gfile.Exists(self.data_source.output_base_dir):
            gfile.DeleteRecursively(self.data_source.output_base_dir)
        if gfile.Exists(self.raw_data_dir):
            gfile.DeleteRecursively(self.raw_data_dir)
        self.kvstore = mysql_client.DBClient('test_cluster', 'localhost:2379',
                                              'test_user', 'test_password',
                                              'fedlearner', True)
        self.kvstore.delete_prefix(common.data_source_kvstore_base_dir(self.data_source.data_source_meta.name))
        self.total_raw_data_count = 0
        self.total_example_id_count = 0
        self.manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
            self.kvstore, self.data_source)
        self.g_data_block_index = 0
        self.version = version 

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
            idx = 0
            for example_idx in cands:
                # mimic negative sample
                if idx % 7 == 0:
                    idx += 1
                    continue
                idx += 1
                feat = {}
                example_id = '{}'.format(example_idx).encode()
                feat['example_id'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[example_id]))
                event_time = 150000000 + example_idx + 1
                feat['event_time'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[event_time]))
                if self.version == Version.V2:
                    feat['id_type'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=['IMEI'.encode()]))
                    feat['type'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[b'1']))
                    feat['req_id'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[example_id]))
                    feat['cid'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[example_id]))

                example = tf.train.Example(features=tf.train.Features(feature=feat))
                builder.append_item(TfExampleItem(example.SerializeToString()),
                                    useless_index, useless_index)
                useless_index += 1

                feat = {}
                feat['example_id'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[example_id]))
                event_time = 150000000 + example_idx + 111
                feat['event_time'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[event_time]))
                if self.version == Version.V2:
                    feat['id_type'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=['IMEI'.encode()]))
                    feat['type'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[b'1']))
                    feat['req_id'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[example_id]))
                    feat['cid'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[example_id]))
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
            example_id_batch = dj_pb.LiteExampleIds(
                    partition_id=0,
                    begin_index=req_index * 512
                )
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
            for example_idx in cands:
                example_id = '{}'.format(example_idx).encode()
                example_id_batch.example_id.append(example_id)
                example_id_batch.event_time.append(150000000 + example_idx)
                if self.version == Version.V2:
                    click_id = '%s_%s'%(example_id.decode(), example_id.decode())
                    example_id_batch.click_id.append(click_id.encode())
                    example_id_batch.id_type.append('IMEI'.encode())
                    example_id_batch.event_time_deep.append(150000000 + example_idx + 1)
                    example_id_batch.type.append(b'1')
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

    def tearDown(self):
        if gfile.Exists(self.data_source.output_base_dir):
            gfile.DeleteRecursively(self.data_source.output_base_dir)
        if gfile.Exists(self.raw_data_dir):
            gfile.DeleteRecursively(self.raw_data_dir)
        self.kvstore.delete_prefix(common.data_source_kvstore_base_dir(self.data_source.data_source_meta.name))

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

from google.protobuf import text_format, empty_pb2

import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join import common

class RawDataPublisher(object):
    def __init__(self, kvstore, raw_data_pub_dir):
        self._kvstore = kvstore
        self._raw_data_pub_dir = raw_data_pub_dir

    def publish_raw_data(self, partition_id, fpaths, timestamps=None):
        if not fpaths:
            logging.warning("no raw data will be published")
            return
        if timestamps is not None and len(fpaths) != len(timestamps):
            raise RuntimeError("the number of raw data file "\
                               "and timestamp mismatch")
        new_raw_data_pubs = []
        for index, fpath in enumerate(fpaths):
            if not gfile.Exists(fpath):
                raise ValueError('{} is not existed'.format(fpath))
            raw_data_pub = dj_pb.RawDatePub(
                    raw_data_meta=dj_pb.RawDataMeta(
                        file_path=fpath,
                        start_index=-1
                    )
                )
            if timestamps is not None:
                raw_data_pub.raw_data_meta.timestamp.MergeFrom(
                        timestamps[index]
                    )
            new_raw_data_pubs.append(raw_data_pub)
        next_pub_index = None
        item_index = 0
        data = text_format.MessageToString(new_raw_data_pubs[item_index])
        while item_index < len(new_raw_data_pubs):
            next_pub_index = self._forward_pub_index(partition_id,
                                                     next_pub_index)
            if self._check_finish_tag(partition_id, next_pub_index-1):
                logging.warning("partition %d has been published finish tag "\
                                "at index %d", partition_id, next_pub_index-1)
                break
            kvstore_key = common.raw_data_pub_kvstore_key(
                                                    self._raw_data_pub_dir,
                                                    partition_id,
                                                    next_pub_index)
            if self._kvstore.cas(kvstore_key, None, data):
                logging.info("Success publish %s at index %d for partition"\
                             "%d", data, next_pub_index, partition_id)
                next_pub_index += 1
                item_index += 1
                if item_index < len(new_raw_data_pubs):
                    raw_data_pub = new_raw_data_pubs[item_index]
                    data = text_format.MessageToString(raw_data_pub)
        if item_index < len(new_raw_data_pubs) - 1:
            logging.warning("%d files are not published since meet finish "\
                            "tag for partition %d. list following",
                            len(new_raw_data_pubs) - item_index, partition_id)
            for idx, pub in enumerate(new_raw_data_pubs[item_index:]):
                logging.warning("%d. %s", idx, pub.raw_data_meta.file_path)

    def finish_raw_data(self, partition_id):
        data = text_format.MessageToString(
                dj_pb.RawDatePub(raw_data_finished=empty_pb2.Empty())
            )
        next_pub_index = None
        while True:
            next_pub_index = self._forward_pub_index(partition_id,
                                                     next_pub_index)
            if self._check_finish_tag(partition_id, next_pub_index-1):
                logging.warning("partition %d has been published finish tag"\
                                "at index %d", partition_id,
                                next_pub_index-1)
                break
            kvstore_key = common.raw_data_pub_kvstore_key(
                                                    self._raw_data_pub_dir,
                                                    partition_id,
                                                    next_pub_index)
            if self._kvstore.cas(kvstore_key, None, data):
                logging.info("Success finish raw data for partition"\
                             "%d", partition_id)
                break

    def _forward_pub_index(self, partition_id, next_pub_index):
        if next_pub_index is None:
            left_index = 0
            right_index = 1 << 63
            while left_index <= right_index:
                index = (left_index + right_index) // 2
                kvstore_key = common.raw_data_pub_kvstore_key(
                        self._raw_data_pub_dir, partition_id, index
                    )
                if self._kvstore.get_data(kvstore_key) is not None:
                    left_index = index + 1
                else:
                    right_index = index - 1
            return right_index + 1
        while True:
            kvstore_key = common.raw_data_pub_kvstore_key(
                                                    self._raw_data_pub_dir,
                                                    partition_id,
                                                    next_pub_index)
            if self._kvstore.get_data(kvstore_key) is None:
                return next_pub_index
            next_pub_index += 1

    def _check_finish_tag(self, partition_id, last_index):
        if last_index >= 0:
            kvstore_key = common.raw_data_pub_kvstore_key(
                                                    self._raw_data_pub_dir,
                                                    partition_id,
                                                    last_index)
            data = self._kvstore.get_data(kvstore_key)
            if data is not None:
                pub_item = text_format.Parse(data, dj_pb.RawDatePub(),
                                             allow_unknown_field=True)
                return pub_item.HasField('raw_data_finished')
        return False

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

from tensorflow.compat.v1 import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join import common

class RawDataPublisher(object):
    def __init__(self, etcd, raw_data_pub_dir):
        self._etcd = etcd
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
            etcd_key = common.raw_data_pub_etcd_key(self._raw_data_pub_dir,
                                                    partition_id,
                                                    next_pub_index)
            if self._etcd.cas(etcd_key, None, data):
                logging.info("Success publish %s at index %d for partition"\
                             "%d", data, next_pub_index, partition_id)
                next_pub_index += 1
                item_index += 1
                if item_index < len(new_raw_data_pubs):
                    raw_data_pub = new_raw_data_pubs[item_index]
                    data = text_format.MessageToString(raw_data_pub)

    def finish_raw_data(self, partition_id):
        data = text_format.MessageToString(
                dj_pb.RawDatePub(raw_data_finished=empty_pb2.Empty())
            )
        next_pub_index = None
        while True:
            next_pub_index = self._forward_pub_index(partition_id,
                                                     next_pub_index)
            etcd_key = common.raw_data_pub_etcd_key(self._raw_data_pub_dir,
                                                    partition_id,
                                                    next_pub_index)
            if self._etcd.cas(etcd_key, None, data):
                logging.info("Success finish raw data for partition"\
                             "%d", partition_id)
                break

    def _forward_pub_index(self, partition_id, next_pub_index):
        if next_pub_index is None:
            left_index = 0
            right_index = 1 << 63
            while left_index <= right_index:
                index = (left_index + right_index) // 2
                etcd_key = common.raw_data_pub_etcd_key(
                        self._raw_data_pub_dir, partition_id, index
                    )
                if self._etcd.get_data(etcd_key) is not None:
                    left_index = index + 1
                else:
                    right_index = index - 1
            return right_index + 1
        while True:
            etcd_key = common.raw_data_pub_etcd_key(self._raw_data_pub_dir,
                                                    partition_id,
                                                    next_pub_index)
            if self._etcd.get_data(etcd_key) is None:
                return next_pub_index
            next_pub_index += 1

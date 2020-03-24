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

import argparse
import logging
from os import path

from google.protobuf import empty_pb2

from tensorflow.compat.v1 import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType

class RawDataController(object):
    def __init__(self, data_source, master_client):
        self._data_source = data_source
        self._master_client = master_client

    def add_raw_data(self, partition_id, fpaths, dedup):
        self._check_partition_id(partition_id)
        if not fpaths:
            raise RuntimeError("no files input")
        for fpath in fpaths:
            if not gfile.Exists(fpath):
                raise ValueError('{} is not existed' % format(fpath))
        rdreq = dj_pb.RawDataRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    partition_id=partition_id,
                    raw_data_fpaths=dj_pb.RawDataFilePaths(
                        file_paths=fpaths, dedup=dedup
                    )
                )
        return self._master_client.AddRawData(rdreq)

    def finish_raw_data(self, partition_id):
        self._check_partition_id(partition_id)
        request = dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                partition_id=partition_id,
                finish_raw_data=empty_pb2.Empty()
            )
        return self._master_client.FinishRawData(request)

    def _check_partition_id(self, partition_id):
        partition_num = self._data_source.data_source_meta.partition_num
        if partition_id < 0 or partition_id >= partition_num:
            raise RuntimeError("partition id {} out of range [{}, {})".format(
                                partition_id, 0, partition_num))

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    parser = argparse.ArgumentParser(description='Raw Data Controller')
    parser.add_argument('cmd', type=str, choices=['finish', 'add'],
                        help='the command for raw data controller, '\
                             'only support add/finish')
    parser.add_argument('master_addr', type=str,
                        help='the addr(uuid) of local data_join_master')
    parser.add_argument('partition_id', type=int,
                        help='the partition to control')
    parser.add_argument('--files', type=str, nargs='+',
                        help='the need raw data fnames')
    parser.add_argument('--src_dir', type=str,
                        help='the directory of input raw data. The input '\
                             'file sequence is sorted by file name and rank '\
                             'after raw data input by --files')
    parser.add_argument('--dedup', action='store_true',
                        help='dedup the input files, otherwise, '\
                             'error if dup input files')
    args = parser.parse_args()
    master_channel = make_insecure_channel(args.master_addr,
                                           ChannelType.INTERNAL)
    master_cli = dj_grpc.DataJoinMasterServiceStub(master_channel)
    data_src = master_cli.GetDataSource(empty_pb2.Empty())
    rdc = RawDataController(data_src, master_cli)
    if args.cmd == 'add':
        all_fpaths = []
        if args.files is not None:
            for fp in args.files:
                all_fpaths.append(fp)
        if args.src_dir is not None:
            dir_fpaths = \
                    [path.join(args.src_dir, f)
                     for f in gfile.ListDirectory(args.src_dir)
                     if not gfile.IsDirectory(path.join(args.src_dir, f))]
            dir_fpaths.sort()
            all_fpaths += dir_fpaths
        if not all_fpaths:
            raise RuntimeError("no raw data files supply")
        status = rdc.add_raw_data(args.partition_id, all_fpaths, args.dedup)
        if status.code != 0:
            logging.error("Failed to add raw data for partition %d reason "\
                          "%s", args.partition_id, status.error_message)
        else:
            logging.info("Success add following %d raw data file for "\
                         "partition %d", len(all_fpaths), args.partition_id)
            for idx, fp in enumerate(all_fpaths):
                logging.info("%d. %s", idx, fp)
    else:
        assert args.cmd == 'finish'
        status = rdc.finish_raw_data(args.partition_id)
        if status.code != 0:
            logging.error("Failed to finish raw data for partition %d, "\
                          "reason %s", args.partition_id, status.error_message)
        else:
            logging.info('Success finish raw data for partition %d',
                         args.partition_id)

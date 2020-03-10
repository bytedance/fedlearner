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
import os
import logging
import uuid
import ntpath

from google.protobuf import empty_pb2

from tensorflow.python.platform import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType

from fedlearner.data_join import visitor
from fedlearner.data_join.common import (
    RawDataIndexSuffix, RawDataUnIndexSuffix, RawDataTmpSuffix
)

class RawDataController(object):
    def __init__(self, data_source, master_client):
        self._data_source = data_source
        self._master_client = master_client

    def copy_files_to_raw_data_dir(self, partition_id, fpaths):
        if len(fpaths) == 0:
            raise RuntimeError("no files input")
        raw_data_dir = self._raw_data_dir(partition_id)
        if not gfile.Exists(raw_data_dir):
            gfile.MakeDirs(raw_data_dir)
        for fpath in fpaths:
            fname = ntpath.basename(fpath)
            dstfpath = os.path.join(raw_data_dir, fname)
            if ntpath.dirname(fpath) != raw_data_dir and \
                    not gfile.Exists(dstfpath):
                tmpfname = str(uuid.uuid1()) + RawDataTmpSuffix
                tmpfpath = os.path.join(raw_data_dir, tmpfname)
                gfile.Copy(fpath, tmpfpath)
                gfile.Rename(tmpfpath, dstfpath)

    def add_raw_data(self, partition_id, fnames):
        if not fnames:
            raise RuntimeError("no files input")
        raw_data_dir = self._raw_data_dir(partition_id)
        for fname in fnames:
            if ntpath.basename(fname) != fname:
                raise ValueError('{} is not a pure file name'.format(fname))
            if fname.endswith(RawDataIndexSuffix) or \
                    fname.endswith(RawDataUnIndexSuffix) or \
                    fname.endswith(RawDataTmpSuffix):
                raise ValueError("the new add fname {} should't endswith " \
                                 "{} or {}".format(fname, RawDataIndexSuffix,
                                  RawDataUnIndexSuffix))
            fpath = os.path.join(raw_data_dir, fname)
            if not gfile.Exists(fpath):
                raise ValueError('{} is not existed at directory {}'\
                                 .format(fname, raw_data_dir))
        next_process_index = self._next_process_index(partition_id)
        for fname in fnames:
            self._rename_to_unindex_fname(partition_id, fname,
                                          next_process_index)
            next_process_index += 1
        return self._update_next_process_index(partition_id,
                                               next_process_index)

    def finish_raw_data(self, partition_id):
        request = dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                partition_id=partition_id,
                finish_raw_data=empty_pb2.Empty()
            )
        return self._master_client.FinishRawData(request)

    def _raw_data_dir(self, partition_id):
        return os.path.join(self._data_source.raw_data_dir,
                            'partition_{}'.format(partition_id))

    def _next_process_index(self, partition_id):
        rdreq = dj_pb.RawDataRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    partition_id=partition_id
                )
        manifest = self._master_client.QueryRawDataManifest(rdreq)
        next_process_index = manifest.next_process_index
        raw_data_dir = self._raw_data_dir(partition_id)
        while True:
            uindex_fname = visitor.encode_unindex_fname(next_process_index,
                                                        RawDataUnIndexSuffix)
            fpath = os.path.join(raw_data_dir, uindex_fname)
            if not gfile.Exists(fpath):
                return next_process_index
            next_process_index += 1

    def _rename_to_unindex_fname(self, partition_id, fname, next_process_index):
        raw_data_dir = self._raw_data_dir(partition_id)
        unindex_fname = visitor.encode_unindex_fname(next_process_index,
                                                     RawDataUnIndexSuffix)
        unindex_fpath = os.path.join(raw_data_dir, unindex_fname)
        gfile.Rename(os.path.join(raw_data_dir, fname), unindex_fpath)

    def _update_next_process_index(self, partition_id, next_process_index):
        rdreq = dj_pb.RawDataRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    partition_id=partition_id,
                    next_process_index=dj_pb.RawDataNextProcessIndex(
                            process_index=next_process_index
                        )
                )
        return self._master_client.AddRawData(rdreq)

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
                    [os.path.join(args.src_dir, f)
                     for f in gfile.ListDirectory(args.src_dir)
                     if (not gfile.IsDirectory(os.path.join(args.src_dir, f))
                         and not f.endswith(RawDataIndexSuffix)
                         and not f.endswith(RawDataUnIndexSuffix)
                         and not f.endswith(RawDataTmpSuffix))]
            dir_fpaths.sort()
            all_fpaths += dir_fpaths
        if not all_fpaths:
            raise RuntimeError("no raw data files supply")
        rdc.copy_files_to_raw_data_dir(args.partition_id, all_fpaths)
        all_fnames = [ntpath.basename(fpath) for fpath in all_fpaths]
        status = rdc.add_raw_data(args.partition_id, all_fnames)
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

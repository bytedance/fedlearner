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
from concurrent import futures
import threading
import argparse
import os
import grpc
from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.common import trainer_master_service_pb2_grpc as tm_grpc
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common.utils import random_shuffle
from fedlearner.data_join.data_block_visitor import DataBlockVisitor
from fedlearner.trainer_master.data.data_block_queue import DataBlockQueue

from .trainer_master_service import TrainerMasterServer

kvstore_type = os.environ.get('KVSTORE_TYPE', 'etcd')

class LeaderTrainerMaster(object):
    class _DataSourceInfo:
        def __init__(self, data_source, data_source_type,
                     start_time, end_time,
                     kvstore_use_mock):
            self.checkpoint_mutex = threading.Lock()
            self.allocated_data_block_ids = None
            self.data_block_queue = DataBlockQueue()
            self.data_block_visitor = DataBlockVisitor(
                data_source, kvstore_type, kvstore_use_mock)
            self.start_time = start_time
            self.end_time = end_time
            self.visited_data_blocks = set()
            self.lock = threading.Lock()
            self.data_source_type = data_source_type

    def __init__(self, application_id, data_source,
                 local_data_sources, start_time, end_time,
                 local_start_times, local_end_times, online_training,
                 shuffle_data_block, shuffle_range, epoch_num):
        self._application_id = application_id
        self._online_training = online_training
        self._status_mutex = threading.Lock()
        self._status = tm_pb.MasterStatus.CREATED

        kvstore_use_mock = os.environ.get('KVSTORE_USE_MOCK', "off") == "on"
        self._epoch_num = epoch_num
        self._shuffle_data_block = shuffle_data_block
        self._shuffle_range = shuffle_range
        self._data_source_dict = dict()
        self._default_data_source_name = None
        self._data_source_dict[data_source] = self._DataSourceInfo(
            data_source, tm_pb.JOINED, start_time, end_time, kvstore_use_mock)
        if local_data_sources:
            for idx, ds in enumerate(local_data_sources):
                if local_start_times and local_end_times:
                    self._data_source_dict[ds] = self._DataSourceInfo(
                        ds, tm_pb.LOCAL, local_start_times[idx],
                        local_end_times[idx], kvstore_use_mock)
                else:
                    self._data_source_dict[ds] = self._DataSourceInfo(
                        ds, tm_pb.LOCAL, start_time, end_time, kvstore_use_mock)
        else:
            self._default_data_source_name = data_source
        logging.debug("Data sources %s loaded",
                      ','.join(self._data_source_dict.keys()))
        if online_training:
            assert self._epoch_num == 1 and not self._shuffle_data_block, \
                "epoch_num must be 1 and shuffle_data_block must be False " \
                "online_training is set"
        assert self._epoch_num >= 1, \
                "epoch_num {} must >= 1".format(self._epoch_num)

    def run(self, listen_port):
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        tm_grpc.add_TrainerMasterServiceServicer_to_server(
            TrainerMasterServer(self._data_block_response,
                                self._get_checkpoint_fn,
                                self._restore_checkpoint_fn,
                                self._get_data_block_size), self._server)
        self._server.add_insecure_port('[::]:%d' % listen_port)
        self._server.start()
        logging.info('Trainer Master Server start on port[%d].', listen_port)
        self._transfer_status(tm_pb.MasterStatus.CREATED,
                              tm_pb.MasterStatus.INITIALING)
        self._server.wait_for_termination()

    def _transfer_status(self, frm, to, callback_fn=lambda *args: True):
        with self._status_mutex:
            if self._status == frm:
                self._status = to
                return callback_fn()
            logging.warning("%s invalid status transfer, from %d to %d, "
                          "while status is %d", self.__class__.__name__,
                          frm, to, self._status)
            self._status = tm_pb.MasterStatus.ERROR
        return False

    def _check_status(self, callback_fn):
        with self._status_mutex:
            return callback_fn(self._status)
        raise ValueError("unreachable")

    def _get_checkpoint_fn(self, request):
        assert request.application_id == self._application_id, \
                "Application id not matched"
        response = tm_pb.GetDataBlockCheckpointResponse()
        ckpt_not_ready_fn = lambda status: status not in \
                (tm_pb.MasterStatus.RUNNING, tm_pb.MasterStatus.FINISHED)
        if self._check_status(ckpt_not_ready_fn):
            response.status.code = common_pb.STATUS_WAIT_FOR_SYNCING_CHECKPOINT
            response.status.error_message = \
                    "master is not ready for querying daya checkpoint"
            return response
        response.status.code = common_pb.STATUS_SUCCESS
        response.status.error_message = 'success'
        for ds_name, ds in self._data_source_dict.items():
            block_info = response.blocks.add()
            block_info.data_source_name = ds_name
            block_info.block_ids.extend(list(ds.allocated_data_block_ids))
        return response

    def _restore_checkpoint_fn(self, request):
        assert request.application_id == self._application_id,\
                "Application id not matched: %s vs %s"%(
                    request.application_id, self._application_id)
        response = tm_pb.RestoreDataBlockCheckpointResponse()
        no_need_restore_fn = lambda status: status in (\
                                            tm_pb.MasterStatus.RUNNING,\
                                            tm_pb.MasterStatus.FINISHED,\
                                            tm_pb.MasterStatus.ERROR)
        if self._check_status(no_need_restore_fn):
            logging.info("No need to restore %s", self.__class__.__name__)
            response.status.code = common_pb.STATUS_SUCCESS
            response.status.error_message = "success"
            return response

        if not request.blocks:  # init case
            logging.info("Init all data source")
            for _, ds_info in self._data_source_dict.items():
                # In case of race, load data before state transfering to
                # RUNNING, and after filling data checkpoint
                with ds_info.checkpoint_mutex:
                    ds_info.allocated_data_block_ids = set()
                self._load_data(ds_info)
        else:
            for ds_info in request.blocks:
                data_source_name = ds_info.data_source_name
                if data_source_name not in self._data_source_dict:
                    if self._default_data_source_name is None:
                        response.status.code = \
                            common_pb.STATUS_DATA_SOURCE_NOT_EXIST
                        response.status.error_message = \
                            "Data source {} not exist".format(data_source_name)
                        return response
                    data_source_name = self._default_data_source_name
                data_source_info = self._data_source_dict[data_source_name]
                # In case of race, load data before state transfering to
                # RUNNING, and after filling data checkpoint
                with data_source_info.checkpoint_mutex:
                    data_source_info.allocated_data_block_ids = set(
                        ds_info.block_ids)
                self._load_data(data_source_info)

        trans_ok = self._transfer_status(tm_pb.MasterStatus.INITIALING,
                             tm_pb.MasterStatus.RUNNING)
        if not trans_ok:
            response.status.code = common_pb.STATUS_WAIT_FOR_SYNCING_CHECKPOINT
            response.status.error_message = \
                    "must sync data checkpoint before alloc"
            return response

        response.status.code = common_pb.STATUS_SUCCESS
        response.status.error_message = "success"
        return response

    def _data_block_response(self, request):
        response = tm_pb.DataBlockResponse()
        def status_check_fn(status):
            response = tm_pb.DataBlockResponse()
            if status in (tm_pb.MasterStatus.FINISHED, \
                    tm_pb.MasterStatus.ERROR):
                response.status.code = common_pb.STATUS_DATA_FINISHED
                response.status.error_message = 'datablock finished'
                return response
            if status != tm_pb.MasterStatus.RUNNING:
                response.status.code = \
                       common_pb.STATUS_WAIT_FOR_SYNCING_CHECKPOINT
                response.status.error_message = \
                        "must sync data checkpoint before alloc"
                return response
            #only if status is RUNNING
            return True

        ready = self._check_status(status_check_fn)
        if ready is not True:
            return ready

        data_source_name = request.data_source_name
        if data_source_name not in self._data_source_dict:
            if self._default_data_source_name is None:
                response.status.code = common_pb.STATUS_DATA_SOURCE_NOT_EXIST
                response.status.error_message = \
                    "Data source {} not exist".format(data_source_name)
                return response
            data_source_name = self._default_data_source_name

        data_source_info = self._data_source_dict[data_source_name]
        data_block = self._alloc_data_block(data_source_info,
                                            block_id=request.block_id)
        if data_block:
            logging.debug("%s allocated worker_%d with block id %s of"
                          " source %s",
                          self.__class__.__name__,
                          request.worker_rank,
                          data_block.block_id,
                          data_source_name)
            response.status.code = common_pb.STATUS_SUCCESS
            response.status.error_message = 'success'
            response.data_block_info.data_path = \
                str(data_block.data_block_fpath)
            response.data_block_info.meta_path = ''
            response.data_block_info.block_id = str(data_block.block_id)
        elif self._online_training:
            logging.debug("%s allocated worker_%d with empty data block. "\
                          "wait for new data block since online traning",
                          self.__class__.__name__, request.worker_rank)
            response.status.code = common_pb.STATUS_NO_MORE_DATA
            response.status.error_message = 'please wait for datablock ready'
        else:
            logging.debug("%s allocated worker_%d with empty data block. "\
                          "exit running since since batch traning",
                          self.__class__.__name__, request.worker_rank)
            response.status.code = common_pb.STATUS_DATA_FINISHED
            response.status.error_message = 'datablock finished'
        if response.status.code == common_pb.STATUS_DATA_FINISHED:
            self._transfer_status(tm_pb.MasterStatus.RUNNING,
                                  tm_pb.MasterStatus.FINISHED)
        return response

    def _get_data_block_size(self, request):
        response = tm_pb.GetDataSourceInfoResponse()
        def status_check_fn(status):
            response = tm_pb.DataBlockResponse()
            if status in (tm_pb.MasterStatus.FINISHED, \
                          tm_pb.MasterStatus.ERROR):
                response.status.code = common_pb.STATUS_DATA_FINISHED
                response.status.error_message = 'datablock finished'
                return response
            #only if status is RUNNING
            return True

        ready = self._check_status(status_check_fn)
        if ready is not True:
            return ready

        data_source_name = request.data_source_name
        if data_source_name not in self._data_source_dict:
            if self._default_data_source_name is None:
                response.status.code = common_pb.STATUS_DATA_SOURCE_NOT_EXIST
                response.status.error_message = \
                    "Data source {} not exist".format(data_source_name)
                return response
            data_source_name = self._default_data_source_name
        data_source_info = self._data_source_dict[data_source_name]
        # block_id is unused in leader role
        with data_source_info.lock:
            response.status.code = common_pb.STATUS_SUCCESS
            response.status.error_message = 'success'
            response.type = data_source_info.data_source_type
            response.size = data_source_info.data_block_visitor.CountDataBlock(
                data_source_info.start_time, data_source_info.end_time)
            return response

    def _load_data(self, data_source_info):
        checkpoint = data_source_info.allocated_data_block_ids
        # pylint: disable=line-too-long
        logging.info("load_data, checkpoint: %s", checkpoint)
        data_block_reps = [
            dbr for dbr in data_source_info.data_block_visitor
                .LoadDataBlockRepByTimeFrame(data_source_info.start_time,
                                             data_source_info.end_time).values()
            if dbr.block_id not in checkpoint and
               dbr.block_id not in data_source_info.visited_data_blocks]

        data_source_info.visited_data_blocks.update([i.block_id for i
                                                     in data_block_reps])

        if self._online_training:
            data_block_reps.sort(key=lambda x: x.data_block_index)
        else:
            data_block_reps.sort(key=lambda x: x.start_time)
        for rnd in range(self._epoch_num):
            if self._shuffle_data_block:
                random_shuffle(data_block_reps, self._shuffle_range)
            for dbr in data_block_reps:
                logging.debug('epoch round-%d: add data block id %s path %s',
                              rnd, dbr.block_id, dbr.data_block_fpath)
                data_source_info.data_block_queue.put(dbr)

    def _alloc_data_block(self, data_source_info, block_id=None):
        # block_id is unused in leader role
        with data_source_info.lock:
            if data_source_info.data_block_queue.empty() and \
                self._online_training:
                logging.info("Load data when queue empty and online training")
                self._load_data(data_source_info)

            if data_source_info.data_block_queue.empty():
                logging.info("Allocate when data_block_queue is empty")
                return None

            data_blocks_resp = data_source_info.data_block_queue.get()
            with data_source_info.checkpoint_mutex:
                data_source_info.allocated_data_block_ids.add(
                    data_blocks_resp.block_id)
            return data_blocks_resp


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser('leader trainer master cmd.')
    parser.add_argument('-p', '--port', type=int, default=50001,
                        help='Listen port of leader trainer master')
    parser.add_argument('-app_id', '--application_id',
                        required=True, help='application_id')
    parser.add_argument('-data_source', '--data_source',
                        required=False, help='training example data source')
    parser.add_argument('-local_data_sources', '--local_data_sources',
                        required=False, default=None,
                        help="local training example data sources,"
                             " split by ','")
    parser.add_argument('-start_date', '--start_date',
                        default=None, help='training data start date')
    parser.add_argument('-end_date', '--end_date',
                        default=None, help='training data end date')
    parser.add_argument('-local_data_start_dates', '--local_data_start_date',
                        default=None, help='local training data start date')
    parser.add_argument('-local_data_end_dates', '--local_data_end_date',
                        default=None, help='local training data end date')
    parser.add_argument('--online_training', action='store_true',
                        help='the train master run for online training')
    parser.add_argument('--shuffle_data_block', action='store_true',
                        help='shuffle the data block or not')
    parser.add_argument('-shuffle_range', '--shuffle_range', type=int,
                        default=0,
                        help='number of data blocks to shuffle')
    parser.add_argument('--epoch_num', type=int, default=1,
                        help='number of epoch for training, not '\
                             'support in online training')
    FLAGS = parser.parse_args()

    start_date = int(FLAGS.start_date) if FLAGS.start_date else None
    end_date = int(FLAGS.end_date) if FLAGS.end_date else None
    local_data_source_list = FLAGS.local_data_sources.split(',') \
        if FLAGS.local_data_sources else []
    local_data_start_dates = FLAGS.local_data_start_dates.split(',') \
        if FLAGS.local_data_start_dates else []
    local_data_start_dates = [int(d) for d in local_data_start_dates]
    local_data_end_dates = FLAGS.local_data_end_dates.split(',') \
        if FLAGS.local_data_end_dates else []
    local_data_end_dates = [int(d) for d in local_data_end_dates]
    leader_tm = LeaderTrainerMaster(FLAGS.application_id, FLAGS.data_source,
                                    local_data_source_list,
                                    start_date, end_date,
                                    local_data_start_dates,
                                    local_data_end_dates,
                                    FLAGS.online_training,
                                    FLAGS.shuffle_data_block,
                                    FLAGS.shuffle_range,
                                    FLAGS.epoch_num)
    leader_tm.run(listen_port=FLAGS.port)

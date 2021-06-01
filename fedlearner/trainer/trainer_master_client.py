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

import os
import time
import grpc

from fedlearner.common import fl_logging
from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.common import trainer_master_service_pb2_grpc as tm_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType
from fedlearner.common import common_pb2 as common_pb


class _TrainerMasterClient(object):
    def __init__(self, client, worker_rank,
                 worker_type=tm_pb.WorkerType.REMOTE_WORKER):
        self._worker_rank = worker_rank
        self._client = client
        self._worker_type = worker_type

    def request_data_block(self, block_id, data_source_type=tm_pb.JOINED):
        request = tm_pb.DataBlockRequest(
            worker_rank=self._worker_rank,
            block_id=block_id,
            worker_type=self._worker_type)
        response = _grpc_with_retry(
            lambda: self._client.RequestDataBlock(request))
        while response.status.code == \
            common_pb.StatusCode.STATUS_WAIT_FOR_DATA_BLOCK:
            fl_logging.info("Sleep 5s to wait for data block of type %s",
                            data_source_type)
            time.sleep(5)
            response = _grpc_with_retry(
                lambda: self._client.RequestDataBlock(request))
        if response.status.code == common_pb.StatusCode.STATUS_SUCCESS:
            fl_logging.debug("succeeded to get datablock, id:%s, data_path: %s",
                          response.block_id, response.data_path)
            return response
        if response.status.code == \
            common_pb.StatusCode.STATUS_INVALID_DATA_BLOCK:
            fl_logging.error("invalid data block id: %s", request.block_id)
            return None
        if response.status.code == common_pb.StatusCode.STATUS_DATA_FINISHED:
            fl_logging.info("data block finished")
            return None
        raise RuntimeError("RequestDataBlock error, code: %s, msg: %s"% \
            (common_pb.StatusCode.Name(response.status.code),
             response.status.error_message))

    def worker_register(self, cluster_def=None):
        request = tm_pb.WorkerRegisterRequest(
            worker_rank=self._worker_rank,
            hostname=os.uname().nodename,
            cluster_def=cluster_def)
        while True:
            response = _grpc_with_retry(
                lambda: self._client.WorkerRegister(request))
            if response.status.code == common_pb.StatusCode.STATUS_SUCCESS:
                return True
            if response.status.code == \
                common_pb.StatusCode.STATUS_WAIT_FOR_SYNCING_CHECKPOINT:
                fl_logging.info("waiting master ready...")
                time.sleep(1)
                continue
            if response.status.code == \
                common_pb.StatusCode.STATUS_DATA_FINISHED:
                fl_logging.info("master completed, ignore worker register")
                return False
            raise RuntimeError("WorkerRegister error, code: %s, msg: %s"% \
                (common_pb.StatusCode.Name(response.status.code),
                response.status.error_message))

    def worker_complete(self, timestamp):
        request = tm_pb.WorkerCompleteRequest(
            worker_rank=self._worker_rank,
            timestamp=timestamp)
        response = _grpc_with_retry(
            lambda: self._client.WorkerComplete(request))
        if response.status.code != common_pb.STATUS_SUCCESS:
            raise RuntimeError("WorkerComplete error, code: %s, msg: %s"% \
                (common_pb.StatusCode.Name(response.status.code),
                 response.status.error_message))

    def wait_master_complete(self):
        request = tm_pb.IsCompletedRequest()
        while True:
            response = _grpc_with_retry(
                lambda: self._client.IsCompleted(request))
            if response.completed:
                fl_logging.info("master completed")
                return
            fl_logging.info("waiting master complete...")
            time.sleep(2)


class TrainerMasterClient(_TrainerMasterClient):
    def __init__(self, address, worker_rank, worker_type):
        channel = make_insecure_channel(
            address,
            mode=ChannelType.INTERNAL,
            options=(
                ('grpc.max_send_message_length', -1),
                ('grpc.max_receive_message_length', -1),
                ('grpc.max_reconnect_backoff_ms', 1000),
            )
        )
        client = tm_grpc.TrainerMasterServiceStub(channel)
        super(TrainerMasterClient, self).__init__(client, worker_rank,
                                                  worker_type)


class LocalTrainerMasterClient(_TrainerMasterClient):
    def __init__(self, local_master, worker_rank):
        super(LocalTrainerMasterClient, self).__init__(
            LocalTrainerMasterClient._LocalGrpcWrapper(local_master),
            worker_rank)

    class _LocalGrpcWrapper(object):
        def __init__(self, master):
            self._master = master

        def RequestDataBlock(self, request):
            return self._master.RequestDataBlock(
                request, _LocalServicerContext())

        def WorkerRegister(self, request):
            return self._master.WorkerRegister(
                request, _LocalServicerContext())

        def WorkerComplete(self, request):
            return self._master.WorkerComplete(
                request, _LocalServicerContext())

        def IsCompleted(self, request):
            return self._master.IsCompleted(
                request, _LocalServicerContext())


class _LocalServicerContext(grpc.ServicerContext):
    def invocation_metadata(self):
        return ()

    def peer(self):
        return "local"

    def peer_identities(self):
        return None

    def peer_identity_key(self):
        return None

    def auth_context(self):
        return dict()

    def set_compression(self, compression):
        return grpc.Compression.NoCompression

    def send_initial_metadata(self, initial_metadata):
        pass

    def set_trailing_metadata(self, trailing_metadata):
        pass

    def abort(self, code, details):
        pass

    def abort_with_status(self, status):
        pass

    def set_code(self, code):
        pass

    def set_details(self, details):
        pass

    def disable_next_message_compression(self):
        pass

    def is_active(self):
        return True

    def time_remaining(self):
        return None

    def cancel(self):
        pass

    def add_callback(self, callback):
        pass

def _grpc_with_retry(call, interval=1):
    while True:
        try:
            return call()
        except grpc.RpcError as e:
            fl_logging.warning("TrainerMasterClient error, status: %s"
                               ", details: %s, wait %ds for retry",
                               e.code(), e.details(), interval)
            time.sleep(interval)

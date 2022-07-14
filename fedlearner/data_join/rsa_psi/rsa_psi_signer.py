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
import sys
import time
import threading
from concurrent import futures

import grpc
from gmpy2 import powmod # pylint: disable=no-name-in-module

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc

from fedlearner.data_join.common import int2bytes, bytes2int

class RsaPsiSignServer(dj_grpc.RsaPsiSignServiceServicer):
    def __init__(self, psi_sign_fn, bye_fn):
        super(RsaPsiSignServer, self).__init__()
        self._psi_sign_fn = psi_sign_fn
        self._bye_fn = bye_fn

    def SignIds(self, request, context):
        try:
            return self._psi_sign_fn(request)
        except Exception: # pylint: disable=broad-except
            response = dj_pb.SignBlindIdsResponse()
            response.status.code = -1
            response.status.error_message = sys.exc_info()

    def Bye(self, request, context):
        return self._bye_fn()

class RsaPsiSigner(object):
    def __init__(self, rsa_prv_key,
                 offload_processor_number,
                 slow_sign_threshold):
        self._rsa_private_key = rsa_prv_key
        self._process_pool_executor = None
        if offload_processor_number > 0:
            self._process_pool_executor = \
                    futures.ProcessPoolExecutor(offload_processor_number)
        self._slow_sign_threshold = slow_sign_threshold
        self._total_sign_duration = .0
        self._sign_batch_num = 0
        self._slow_sign_batch_num = 0
        self._total_slow_sign_duration = .0
        self._peer_bye = False
        self._cond = threading.Condition()

    def _psi_sign_fn(self, request):
        d, n = self._rsa_private_key.d, self._rsa_private_key.n
        start_tm = time.time()
        response = None
        if self._process_pool_executor is not None:
            rids = [rid for rid in request.ids] # pylint: disable=unnecessary-comprehension
            sign_future = self._process_pool_executor.submit(
                    RsaPsiSigner._psi_sign_impl, rids, d, n
                )
            response = dj_pb.SignIdsResponse(
                    status=common_pb.Status(code=0),
                    signed_ids=sign_future.result()
                )
        else:
            response = dj_pb.SignIdsResponse(
                status=common_pb.Status(code=0),
                signed_ids=RsaPsiSigner._psi_sign_impl(request.ids, d, n)
            )
        self._record_sign_duration(request.begin_index,
                                   len(request.ids),
                                   time.time()-start_tm)
        return response

    def _bye_fn(self):
        with self._cond:
            self._peer_bye = True
            self._cond.notify_all()
        return common_pb.Status(code=0)

    def _record_sign_duration(self, begin_index, batch_len, sign_duration):
        logging_record = False
        with self._cond:
            self._total_sign_duration += sign_duration
            self._sign_batch_num += 1
            if sign_duration >= self._slow_sign_threshold:
                self._total_slow_sign_duration += sign_duration
                self._slow_sign_batch_num += 1
            logging_record = self._sign_batch_num % 32 == 0
        if logging_record:
            avg_duration = self._total_sign_duration \
                    / self._sign_batch_num
            slow_avg_duration = 0.0
            if self._slow_sign_batch_num > 0:
                slow_avg_duration = self._total_slow_sign_duration \
                        / self._slow_sign_batch_num
            logging.warning("%d/%d batch[%d, %d) sign cost more than %d "\
                            "second, avg duration: %f for each batch, avg "\
                            "duration: %f for slow batch",
                            self._slow_sign_batch_num, self._sign_batch_num,
                            begin_index, begin_index+batch_len,
                            self._slow_sign_threshold,
                            avg_duration, slow_avg_duration)

    @staticmethod
    def _psi_sign_impl(items, d, n):
        byte_len = n.bit_length() // 8
        return [int2bytes(powmod(bytes2int(item), d, n).digits(), byte_len)
                for item in items]

    def start(self, listen_port, worker_num):
        self._server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=worker_num)
            )
        dj_grpc.add_RsaPsiSignServiceServicer_to_server(
                RsaPsiSignServer(self._psi_sign_fn, self._bye_fn),
                self._server
            )
        self._server.add_insecure_port('[::]:%d' % listen_port)
        self._server.start()
        logging.info('RsaPsiSigner Server start on port[%d].', listen_port)

    def stop(self):
        self._server.stop(None)
        if self._process_pool_executor is not None:
            self._process_pool_executor.shutdown(True)
        logging.info('RsaPsiSigner Server stopped')

    def _wait_for_peer_bye(self):
        with self._cond:
            while not self._peer_bye:
                self._cond.wait()

    def run(self, listen_port, worker_num):
        self.start(listen_port, worker_num)
        self._wait_for_peer_bye()
        self.stop()

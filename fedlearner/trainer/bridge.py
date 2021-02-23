# Copyright 2020 The FedLearner Authors. All Rights Reserved.

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
# pylint: disable=protected-access

import os
import collections
import logging
import threading
import time
from concurrent import futures

import grpc
import tensorflow.compat.v1 as tf
from google.protobuf import any_pb2 as any_pb
# TODO Wait for PChannel to finish
import fedlearner.bridge as bridge_core

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import metrics
from fedlearner.common import trainer_worker_service_pb2 as tws2_pb
from fedlearner.common import trainer_worker_service_pb2_grpc as tws2_grpc

class Bridge(object):
    class TrainerWorkerServicer(tws2_grpc.TrainerWorkerServiceServicer):
        def __init__(self, bridge):
            super(Bridge.TrainerWorkerServicer, self).__init__()
            self._bridge = bridge

        def StreamTransmit(self, request_iterator, context):
            for request in request_iterator:
                yield self._bridge._transmit_handler(request)

        def LoadDataBlock(self, request, context):
            return self._bridge._data_block_handler(request)

    def __init__(self,
                 role,
                 listen_port,
                 remote_address,
                 app_id=None,
                 rank=0):
        self._role = role
        self._listen_address = "[::]:{}".format(listen_port)
        self._remote_address = remote_address
        if app_id is None:
            app_id = 'test_trainer'
        self._token = "{}-{}".format(app_id, rank)

        self._data_block_handler_fn = None

        self._peer_terminated = False
        self._terminated = False

        # data transmit
        self._condition = threading.Condition()
        self._current_iter_id = None
        self._next_iter_id = 0
        self._received_data = collections.defaultdict(dict)
        self._stream_queue = collections.deque()
        self._stream_terminated = threading.Event()

        # bridge
        self._bridge = bridge_core.Bridge(
            self._listen_address, self._remote_address,
            token=self._token)
        self._bridge.subscribe(self._bridge_callback)

        # client & server
        self._client = tws2_grpc \
            .TrainerWorkerServiceStub(self._bridge)
        tws2_grpc.add_TrainerWorkerServiceServicer_to_server(
            Bridge.TrainerWorkerServicer(self), self._bridge)

    def _bridge_callback(self, bridge, event):
        if event == bridge_core.Bridge.Event.PEER_CLOSED:
            logging.error("peer terminated")
            with self._condition:
                self._peer_terminated = True
                self._condition.notify_all()
        elif event == bridge_core.Bridge.Event.PEER_DISCONNECTED:
            logging.error("Suicide as peer disconnected")
            os._exit(138)
        elif event == bridge_core.Bridge.Event.UNAUTHORIZED:
            logging.error("Suicide as unauthorized")
            os._exit(138)
        elif event == bridge_core.Bridge.Event.UNIDENTIFIED \
            or event == bridge_core.Bridge.Event.PEER_UNIDENTIFIED:
            logging.error('Suicide as peer has restarted!')
            os._exit(138)  # Tell Scheduler to restart myself

    def __del__(self):
        self.terminate()

    @property
    def role(self):
        return self._role

    def connect(self):
        self._bridge.start(wait=True)
        stream_response = self._client.StreamTransmit(self._stream_generator())
        def fn():
            for _ in stream_response:
                pass
        threading.Thread(target=fn).start()

    def terminate(self):
        with self._condition:
            self._terminated = True
            self._condition.notify_all()
        self._stream_terminated.wait()
        self._bridge.stop(wait=True)

    def _stream_generator(self):
        while True:
            with self._condition:
                while len(self._stream_queue) == 0:
                    if self._terminated:
                        self._stream_terminated.set()
                        raise StopIteration
                    self._condition.wait()
                msg = self._stream_queue.popleft()
            yield msg

    def _transmit(self, msg):
        metrics.emit_counter('send_counter', 1)
        with self._condition:
            if self._terminated:
                raise RuntimeError("Bridge was terminated")

            logging.info("transmit send: iter_id: %d, name: %s",
                msg.iter_id, msg.name)
            self._stream_queue.append(msg)
            self._condition.notifyAll()

    def _transmit_handler(self, request):
        metrics.emit_counter('receive_counter', 1)
        with self._condition:
            logging.info("transmit receive, iter_id: %d, name: %s",
                request.iter_id, request.name)
            self._received_data[request.iter_id][request.name] = request
            self._condition.notifyAll()
        return tws2_pb.TransmitResponse(
            status=common_pb.Status(code=common_pb.STATUS_SUCCESS))

    def _data_block_handler(self, request):
        assert self._data_block_handler_fn is not None, \
            "Received DataBlockMessage but no handler registered."
        metrics.emit_counter('load_data_block_counter', 1)
        if self._data_block_handler_fn(request):
            logging.info('Succeeded to load data block %s',
                         request.block_id)
            return tws2_pb.LoadDataBlockResponse(
                status=common_pb.Status(code=common_pb.STATUS_SUCCESS)
            )
        metrics.emit_counter('load_data_block_fail_counter', 1)
        logging.info('Failed to load data block %s', request.block_id)
        return tws2_pb.LoadDataBlockResponse(
            status=common_pb.Status(code=common_pb.STATUS_INVALID_DATA_BLOCK)
        )

    @property
    def current_iter_id(self):
        return self._current_iter_id

    def new_iter_id(self):
        iter_id = self._next_iter_id
        self._next_iter_id += 1
        return iter_id

    def start(self, iter_id):
        assert self._current_iter_id is None, "Last iter not finished"
        self._current_iter_id = iter_id
        logging.debug("Starting iter %d", iter_id)

    def commit(self):
        assert self._current_iter_id is not None, "Not started yet"
        with self._condition:
            last_iter_id = self._current_iter_id
            self._current_iter_id = None
            if last_iter_id in self._received_data:
                del self._received_data[last_iter_id]
        logging.debug("Iter %d committed", last_iter_id)

    def register_data_block_handler(self, func):
        assert self._data_block_handler_fn is None, \
            "DataBlock handler already registered"
        self._data_block_handler_fn = func

    def load_data_block(self, count, block_id):
        req = tws2_pb.LoadDataBlockRequest(count=count, block_id=block_id)
        logging.debug("sending DataBlock with id %s", block_id)
        resp = self._client.LoadDataBlock(req)
        if resp.status.code == common_pb.STATUS_SUCCESS:
            logging.info('Remote succeeded to load data block %s', block_id)
            return True
        logging.info('Remoted failed to load data block %s. code: %d',
                     block_id, resp.status.code)
        return False

    def send(self, iter_id, name, x):
        msg = tws2_pb.TransmitRequest(
            iter_id=iter_id, name=name, tensor=tf.make_tensor_proto(x)
        )
        self._transmit(msg)
        logging.debug('Data: send %s for iter %d', name, iter_id)

    def send_proto(self, iter_id, name, proto):
        any_proto = any_pb.Any()
        any_proto.Pack(proto)
        msg = tws2_pb.TransmitRequest(
            iter_id=iter_id, name=name, any_data=any_proto
        )
        self._transmit(msg)
        logging.debug('Data: send protobuf %s for iter %d', name, iter_id)

    def send_op(self, name, x):
        def func(x):
            assert self._current_iter_id is not None, "Bridge not started"
            self.send(self._current_iter_id, name, x.numpy())

        out = tf.py_function(func=func, inp=[x], Tout=[], name='send_' + name)
        return out

    def receive(self, iter_id, name):
        logging.debug('Data: Waiting to receive %s for iter %d.', name,
                      iter_id)
        start_time = time.time()
        with self._condition:
            while (iter_id not in self._received_data
                   or name not in self._received_data[iter_id]):
                if self._peer_terminated:
                    raise RuntimeError(
                        "loss {} for iter {}".format(name, iter_id))
                self._condition.wait()
            data = self._received_data[iter_id][name]
        duration = time.time() - start_time
        metrics.emit_timer('receive_timer', duration)
        logging.debug(
            'Data: received %s for iter %d after %f sec.',
            name, iter_id, duration)
        return tf.make_ndarray(data.tensor)

    def receive_proto(self, iter_id, name):
        logging.debug('Data: Waiting to receive proto %s for iter %d.',
                      name, iter_id)
        with self._condition:
            while (iter_id not in self._received_data
                   or name not in self._received_data[iter_id]):
                self._condition.wait()
            data = self._received_data[iter_id][name]
        logging.debug('Data: received %s for iter %d.', name, iter_id)
        return data.any_data

    def receive_op(self, name, dtype):
        def func():
            assert self._current_iter_id is not None, "Bridge not started"
            x = self.receive(self._current_iter_id, name)
            return tf.convert_to_tensor(x, dtype=dtype)

        return tf.py_function(func=func, inp=[], Tout=[dtype])[0]

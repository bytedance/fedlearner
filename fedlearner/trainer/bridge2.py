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
# pylint: disable=protected-access

import collections
import logging
import threading
import time
from concurrent import futures

import grpc
import tensorflow.compat.v1 as tf
from google.protobuf import any_pb2, empty_pb2
# TODO Wait for PChannel to finish
from pathtonewChannel import PChannel

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import metrics
from fedlearner.common import trainer_worker_service2_pb2 as tws2_pb
from fedlearner.common import trainer_worker_service2_pb2_grpc as tws2_grpc
from fedlearner.proxy.channel import ChannelType


class Bridge(object):
    class TrainerWorkerServicer(tws2_grpc.TrainerWorkerServiceServicer):
        def __init__(self, bridge):
            super(Bridge.TrainerWorkerServicer, self).__init__()
            self._bridge = bridge

        def Transmit(self, request, context):
            return self._bridge._transmit_handler(request)

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
                 rank=0,
                 streaming_mode=True,
                 compression=grpc.Compression.NoCompression):
        self._role = role
        self._listen_port = listen_port
        self._remote_address = remote_address
        if app_id is None:
            app_id = 'test_trainer'
        self._app_id = app_id
        self._rank = rank
        self._streaming_mode = streaming_mode
        self._compression = compression

        self._data_block_handler_fn = None

        # Connection related
        self._identifier = '%s-%s-%d-%d' % (
            app_id, role, rank, int(time.time()))  # Ensure unique per run
        self._connected = False

        # data transmit
        self._condition = threading.Condition()
        self._current_iter_id = None
        self._next_iter_id = 0
        self._received_data = collections.defaultdict(dict)
        self._stream_queue = collections.deque()
        self._transmitting = True

        # grpc client
        self._grpc_options = [
            ('grpc.max_send_message_length', 2 ** 31 - 1),
            ('grpc.max_receive_message_length', 2 ** 31 - 1)
        ]
        self._persistence_channel = PChannel(
            remote_address, ChannelType.REMOTE,
            options=self._grpc_options, compression=self._compression
        )
        self._client = tws2_grpc \
            .TrainerWorkerServiceStub(self._persistence_channel)
        self._stream_thread = threading.Thread(
            target=self._client.StreamTransmit,
            kwargs={'request_iterator': self._stream_generator()}
        )

        # server
        self._transmit_receive_lock = threading.Lock()
        self._server = PChannel(
            futures.ThreadPoolExecutor(max_workers=10),
            options=self._grpc_options,
            compression=self._compression
        )
        tws2_grpc.add_TrainerWorkerServiceServicer_to_server(
            Bridge.TrainerWorkerServicer(self), self._server
        )
        self._server.add_insecure_port('[::]:%d' % listen_port)

    def __del__(self):
        self.terminate()

    @property
    def role(self):
        return self._role

    # TODO Refactor after PChannel finished.
    @property
    def connected_at(self):
        if self._connected:
            return self._connected_at
        return None

    # TODO Refactor after PChannel finished.
    @property
    def terminated_at(self):
        if self._terminated:
            return self._terminated_at
        return None

    # TODO Refactor after PChannel finished. Might be implemented by PChannel.
    def _stream_generator(self):
        with self._condition:
            while len(self._stream_queue) == 0:
                if not self._transmitting:
                    raise StopIteration
                self._condition.wait()
            yield self._stream_queue.popleft()

    def _transmit(self, msg):
        assert self._connected, "Cannot transmit before connect"
        metrics.emit_counter('send_counter', 1)
        if not self._streaming_mode:
            self._client.Transmit(msg)
        else:
            with self._condition:
                self._stream_queue.append(msg)
                self._condition.notifyAll()

    def _transmit_handler(self, request):
        assert self._connected, "Cannot transmit before connect"
        metrics.emit_counter('receive_counter', 1)
        with self._condition:
            assert request.iter_id in self._received_data
            assert isinstance(request, tws2_pb.TrainerWorkerRequest)
            self._received_data[request.iter_id][request.name] = request
            self._condition.notifyAll()
        return empty_pb2.Empty()

    def _data_block_handler(self, request):
        assert self._connected, "Cannot load data before connect"
        assert self._data_block_handler_fn is not None, \
            "Received DataBlockMessage but no handler registered."
        metrics.emit_counter('load_data_block_counter', 1)
        if self._data_block_handler_fn(request):
            logging.info('Succeeded to load data block %s',
                         request.block_id)
            return tws2_pb.TrainerWorkerResponse(
                status=common_pb.Status(code=common_pb.STATUS_SUCCESS)
            )
        metrics.emit_counter('load_data_block_fail_counter', 1)
        logging.info('Failed to load data block %s', request.block_id)
        return tws2_pb.TrainerWorkerResponse(
            status=common_pb.Status(code=common_pb.STATUS_INVALID_DATA_BLOCK)
        )

    def connect(self):
        with self._condition:
            if not self._connected:
                self._server.start()
                self._persistence_channel.Connect()
                self._stream_thread.start()
                self._connected = True

    def terminate(self):
        with self._condition:
            if self._connected:
                self._transmitting = False
                self._stream_thread.join()
                self._persistence_channel.Close()
                self._server.close()
                self._connected = False

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
        msg = tws2_pb.TrainerWorkerRequest(
            iter_id=iter_id, name=name, tensor=tf.make_tensor_proto(x)
        )
        self._transmit(msg)
        logging.debug('Data: send %s for iter %d. seq_num=%d.',
                      name, iter_id, msg.seq_num)

    def send_proto(self, iter_id, name, proto):
        any_proto = any_pb2.Any()
        any_proto.Pack(proto)
        msg = tws2_pb.TrainerWorkerRequest(
            iter_id=iter_id, name=name, any_data=any_proto
        )
        self._transmit(msg)
        logging.debug('Data: send protobuf %s for iter %d. seq_num=%d.',
                      name, iter_id, msg.seq_num)

    def send_op(self, name, x):
        def func():
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

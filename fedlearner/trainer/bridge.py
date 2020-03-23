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

import time
try:
    import queue
except ImportError:
    import Queue as queue
import logging
import threading
import collections
from concurrent import futures

import grpc
import tensorflow.compat.v1 as tf

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import trainer_worker_service_pb2 as tws_pb
from fedlearner.common import trainer_worker_service_pb2_grpc as tws_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType


class Bridge(object):
    class TrainerWorkerServicer(tws_grpc.TrainerWorkerServiceServicer):
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

        def Connect(self, request, context):
            return self._bridge._connect_handler(request)

        def Heartbeat(self, request, context):
            return self._bridge._heartbeat_handler(request)

    def __init__(self,
                 role,
                 listen_port,
                 remote_address,
                 app_id='test_trainer',
                 rank=0,
                 streaming_mode=True):
        self._role = role
        self._listen_port = listen_port
        self._remote_address = remote_address
        self._app_id = app_id
        self._rank = rank
        self._streaming_mode = streaming_mode

        self._prefetch_handlers = []
        self._data_block_handler_fn = None
        self._connected = False

        # data transmit
        self._condition = threading.Condition()
        self._current_iter_id = None
        self._next_iter_id = 0
        self._received_data = {}

        channel = make_insecure_channel(remote_address, ChannelType.REMOTE)
        self._client = tws_grpc.TrainerWorkerServiceStub(channel)
        self._next_send_seq_num = 0
        self._transmit_queue = queue.Queue()
        self._client_daemon = None
        self._client_daemon_shutdown_fn = None

        # server
        self._next_receive_seq_num = 0
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        tws_grpc.add_TrainerWorkerServiceServicer_to_server(
            Bridge.TrainerWorkerServicer(self), self._server)
        self._server.add_insecure_port('[::]:%d' % listen_port)

    def __del__(self):
        self.terminate()

    def _client_daemon_fn(self):
        shutdown = [False]
        generator = None

        def shutdown_fn():
            shutdown[0] = True
            if generator is not None:
                generator.cancel()
            return generator.result()

        self._client_daemon_shutdown_fn = shutdown_fn

        while not shutdown[0]:
            lock = threading.Lock()
            resend_list = collections.deque()
            try:

                def iterator():
                    for item in resend_list:
                        yield item
                    while True:
                        item = self._transmit_queue.get()
                        with lock:
                            resend_list.append(item)
                        yield item

                generator = self._client.StreamTransmit(iterator())
                for response in generator:
                    if response.status.code != common_pb.STATUS_SUCCESS:
                        raise RuntimeError("Trainsmit failed with %d" %
                                           response.status.code)
                    logging.debug("Transmit success with %d",
                                 response.status.code)
                    with lock:
                        while resend_list and \
                                resend_list[0].seq_num < response.next_seq_num:
                            resend_list.popleft()
            except Exception as e:  # pylint: disable=broad-except
                if not shutdown[0]:
                    logging.warning("Bridge streaming broken: %s. " \
                                    "Retry in 1 second...", repr(e))
                    time.sleep(1)

    def _transmit(self, msg):
        assert self._connected, "Cannot transmit before connect"
        msg.seq_num = self._next_send_seq_num
        self._next_send_seq_num += 1
        if self._streaming_mode:
            self._transmit_queue.put(msg)
        else:
            rsp = self._client.Transmit(msg)
            assert rsp.status.code == common_pb.STATUS_SUCCESS, \
                "Transmit error with code %d."%rsp.status.code

    def _transmit_handler(self, request):
        assert self._connected, "Cannot transmit before connect"
        if request.seq_num >= self._next_receive_seq_num:
            assert request.seq_num == self._next_receive_seq_num, \
                "Invalid request"
            self._next_receive_seq_num += 1

            if request.HasField('start'):
                with self._condition:
                    self._received_data[request.start.iter_id] = {}
            elif request.HasField('commit'):
                pass
            elif request.HasField('data'):
                with self._condition:
                    assert request.data.iter_id in self._received_data
                    self._received_data[
                        request.data.iter_id][
                            request.data.name] = \
                                tf.make_ndarray(request.data.tensor)
                    self._condition.notifyAll()
            elif request.HasField('prefetch'):
                for func in self._prefetch_handlers:
                    func(request.prefetch)
            else:
                return tws_pb.TrainerWorkerResponse(
                    status=common_pb.Status(
                        code=common_pb.STATUS_INVALID_REQUEST),
                    next_seq_num=self._next_receive_seq_num)

        return tws_pb.TrainerWorkerResponse(
            next_seq_num=self._next_receive_seq_num)

    def _data_block_handler(self, request):
        assert self._connected, "Cannot load data before connect"
        if not self._data_block_handler_fn:
            raise RuntimeError("Received DataBlockMessage but" \
                                " no handler registered")
        self._data_block_handler_fn(request)
        return common_pb.Status(code=common_pb.STATUS_SUCCESS)

    def _connect_handler(self, request):
        assert self._role == 'follower', \
            "Leader does not accept connect request"
        assert request.app_id == self._app_id, \
            "Connection failed. Application id mismatch: %s vs %s"%(
                request.app_id, self._app_id)
        assert request.worker_rank == self._rank, \
            "Connection failed. Rank mismatch: %s vs %s"%(
                request.worker_rank, self._rank)

        with self._condition:
            assert not self._connected, "Already connected"
            self._connected = True
            self._condition.notifyAll()

        return tws_pb.ConnectResponse(app_id=self._app_id,
                                      worker_rank=self._rank)

    def _heartbeat_handler(self, request):
        return tws_pb.HeartbeatResponse(app_id=self._app_id,
                                        worker_rank=self._rank,
                                        current_iter_id=self._current_iter_id)

    def connect(self):
        assert not self._connected, "Already connected"
        self._server.start()

        if self._role == 'leader':
            msg = tws_pb.ConnectRequest(app_id=self._app_id,
                                        worker_rank=self._rank)
            while True:
                try:
                    self._client.Connect(msg)
                except Exception as e:  # pylint: disable=broad-except
                    logging.warning("Bridge failed to connect: %s. " \
                                    "Retry in 1 second...",
                                    repr(e))
                    time.sleep(1)
                    continue
                break
            self._connected = True
            logging.debug('Bridge connected as leader')
        else:
            with self._condition:
                while not self._connected:
                    self._condition.wait()
            logging.debug('Bridge connected as follower')

        if self._streaming_mode:
            logging.debug('enter streaming_mode.')
            self._client_daemon = threading.Thread(
                target=self._client_daemon_fn)
            self._client_daemon.start()
        logging.debug('finish connect.')

    def terminate(self):
        try:
            if self._client_daemon_shutdown_fn is not None:
                self._client_daemon_shutdown_fn()
                self._client_daemon.join()
        except Exception:  # pylint: disable=broad-except
            pass
        self._server.stop(None)
        logging.debug("Bridge connection terminated")

    def new_iter_id(self):
        iter_id = self._next_iter_id
        self._next_iter_id += 1
        return iter_id

    def start(self, iter_id):
        assert self._current_iter_id is None, "Last iter not finished"
        self._current_iter_id = iter_id

        msg = tws_pb.TrainerWorkerMessage(start=tws_pb.StartMessage(
            iter_id=iter_id))
        self._transmit(msg)
        logging.debug("Starting iter %d", iter_id)

    def commit(self):
        assert self._current_iter_id is not None, "Not started yet"
        with self._condition:
            last_iter_id = self._current_iter_id
            self._current_iter_id = None
            if last_iter_id in self._received_data:
                del self._received_data[last_iter_id]

        msg = tws_pb.TrainerWorkerMessage(commit=tws_pb.CommitMessage(
            iter_id=last_iter_id))
        self._transmit(msg)
        logging.debug("iter %d committed", last_iter_id)

    def register_data_block_handler(self, func):
        assert self._data_block_handler_fn is None, \
            "DataBlock handler already registered"
        self._data_block_handler_fn = func

    def load_data_block(self, count, block_id):
        msg = tws_pb.LoadDataBlockRequest(count=count, block_id=block_id)
        return self._client.LoadDataBlock(msg)

    def register_prefetch_handler(self, func):
        self._prefetch_handlers.append(func)

    def prefetch(self, iter_id, sample_ids):
        msg = tws_pb.TrainerWorkerMessage(prefetch=tws_pb.PrefetchMessage(
            iter_id=iter_id, sample_ids=sample_ids))
        self._transmit(msg)

    def send(self, iter_id, name, x):
        msg = tws_pb.TrainerWorkerMessage(data=tws_pb.DataMessage(
            iter_id=iter_id, name=name, tensor=tf.make_tensor_proto(x)))
        self._transmit(msg)
        logging.debug('Data: send %s for iter %d.', name, iter_id)

    def send_op(self, name, x):
        def func(x):
            assert self._current_iter_id is not None, "Bridge not started"
            self.send(self._current_iter_id, name, x.numpy())

        out = tf.py_function(func=func, inp=[x], Tout=[], name='send_' + name)
        return out

    def receive(self, iter_id, name):
        logging.debug('Data: Waiting to receive %s for iter %d.', name,
                      iter_id)
        with self._condition:
            while (iter_id not in self._received_data) \
                    or (name not in self._received_data[iter_id]):
                self._condition.wait()
            x = self._received_data[iter_id][name]
        logging.debug('Data: received %s for iter %d.', name, iter_id)
        return x

    def receive_op(self, name, dtype):
        def func():
            assert self._current_iter_id is not None, "Bridge not started"
            x = self.receive(self._current_iter_id, name)
            return tf.convert_to_tensor(x, dtype=dtype)

        return tf.py_function(func=func, inp=[], Tout=[dtype])[0]

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
import logging
import os
import threading
import collections
from concurrent import futures

import grpc
import google.protobuf.any_pb2
import tensorflow.compat.v1 as tf

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import trainer_worker_service_pb2 as tws_pb
from fedlearner.common import trainer_worker_service_pb2_grpc as tws_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType
from fedlearner.common import metrics


def make_ready_client(channel, stop_event=None):
    channel_ready = grpc.channel_ready_future(channel)
    wait_secs = 0.5
    start_time = time.time()
    while (stop_event is None) or (not stop_event.is_set()):
        try:
            channel_ready.result(timeout=wait_secs)
            break
        except grpc.FutureTimeoutError:
            logging.warning(
                'Channel has not been ready for %.2f seconds',
                time.time()-start_time)
            if wait_secs < 5.0:
                wait_secs *= 1.2
        except Exception as e:  # pylint: disable=broad-except
            logging.warning('Waiting channel ready: %s', repr(e))
    return tws_grpc.TrainerWorkerServiceStub(channel)


class _MessageQueue(object):
    def __init__(self, window_size=100):
        super(_MessageQueue, self).__init__()
        self._window_size = window_size
        self._condition = threading.Condition()
        self._queue = collections.deque()
        self._next = 0

    def size(self):
        with self._condition:
            return len(self._queue)

    def confirm(self, next_seq_num):
        with self._condition:
            while self._queue and self._queue[0].seq_num < next_seq_num:
                self._queue.popleft()
                if self._next > 0:
                    self._next -= 1
            self._condition.notifyAll()

    def resend(self, seq_num):
        with self._condition:
            while self._next > 0 and \
                    (self._next >= len(self._queue) or \
                     self._queue[self._next].seq_num > seq_num):
                self._next -= 1
            if self._queue:
                logging.warning(
                    'Message with seq_num=%d missing. Resending from %d',
                    seq_num, self._queue[self._next].seq_num)
            self._condition.notifyAll()

    def put(self, msg):
        with self._condition:
            while len(self._queue) >= self._window_size:
                self._condition.wait()
            self._queue.append(msg)
            self._condition.notifyAll()

    def get(self, event):
        with self._condition:
            while self._next == len(self._queue):
                if not self._condition.wait(10.0) and self._queue:
                    logging.warning(
                        'Timeout waiting for confirmation. Resending from %d',
                        self._queue[0].seq_num)
                    self._next = 0
                if event.is_set():
                    raise StopIteration
            if event.is_set():
                raise StopIteration

            assert self._next < len(self._queue)
            msg = self._queue[self._next]
            self._next += 1
            return msg


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

        def Terminate(self, request, context):
            return self._bridge._terminate_handler(request)

    def __init__(self,
                 role,
                 listen_port,
                 remote_address,
                 app_id=None,
                 rank=0,
                 streaming_mode=True,
                 compression=grpc.Compression.NoCompression,
                 iter_timeout=1800):
        self._role = role
        self._listen_port = listen_port
        self._remote_address = remote_address
        if app_id is None:
            app_id = 'test_trainer'
        self._app_id = app_id
        self._rank = rank
        self._streaming_mode = streaming_mode
        self._compression = compression
        self._iter_timeout = iter_timeout

        self._prefetch_handlers = []
        self._data_block_handler_fn = None

        # Connection related
        self._connected = False
        self._connected_at = 0
        self._terminated = False
        self._terminated_at = 0
        self._peer_terminated = False
        self._identifier = '%s-%s-%d-%d' % (
            app_id, role, rank, int(time.time())) # Ensure unique per run
        self._peer_identifier = ''

        # data transmit
        self._condition = threading.Condition()
        self._iter_started_at = 0
        self._current_iter_id = None
        self._next_iter_id = 0
        self._peer_next_iter_id = 0
        self._received_data = {}

        # grpc client
        self._transmit_send_lock = threading.Lock()
        self._client_lock = threading.Lock()
        self._grpc_options = [
            ('grpc.max_send_message_length', 2**31-1),
            ('grpc.max_receive_message_length', 2**31-1)
        ]
        self._channel = make_insecure_channel(
            remote_address, ChannelType.REMOTE,
            options=self._grpc_options, compression=self._compression)
        self._client = tws_grpc.TrainerWorkerServiceStub(self._channel)
        self._next_send_seq_num = 0
        self._transmit_queue = _MessageQueue()
        self._client_daemon = None
        self._client_daemon_shutdown_fn = None

        # server
        self._transmit_receive_lock = threading.Lock()
        self._next_receive_seq_num = 0
        self._server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=10),
            options=self._grpc_options,
            compression=self._compression)
        tws_grpc.add_TrainerWorkerServiceServicer_to_server(
            Bridge.TrainerWorkerServicer(self), self._server)
        self._server.add_insecure_port('[::]:%d' % listen_port)

    def __del__(self):
        self.terminate()

    @property
    def role(self):
        return self._role

    @property
    def connected_at(self):
        if self._connected:
            return self._connected_at
        return None

    @property
    def terminated_at(self):
        if self._terminated:
            return self._terminated_at
        return None

    def _rpc_with_retry(self, sender, err_log):
        while True:
            with self._client_lock:
                try:
                    return sender()
                except Exception as e:  # pylint: disable=broad-except
                    logging.warning(
                        "%s: %s. Retry in 1s...", err_log, repr(e))
                    metrics.emit_counter('reconnect_counter', 1)
                    self._channel.close()
                    time.sleep(1)
                    self._channel = make_insecure_channel(
                        self._remote_address, ChannelType.REMOTE,
                        options=self._grpc_options,
                        compression=self._compression)
                    self._client = make_ready_client(self._channel)
                    self._check_remote_heartbeat(self._client)

    def _client_daemon_fn(self):
        stop_event = threading.Event()
        generator = None
        channel = make_insecure_channel(
            self._remote_address, ChannelType.REMOTE,
            options=self._grpc_options, compression=self._compression)
        client = make_ready_client(channel, stop_event)

        def shutdown_fn():
            while self._transmit_queue.size():
                logging.debug(
                    "Waiting for message queue's being cleaned. "
                    "Queue size: %d", self._transmit_queue.size())
                time.sleep(1)

            stop_event.set()
            if generator is not None:
                generator.cancel()

        self._client_daemon_shutdown_fn = shutdown_fn

        while not stop_event.is_set():
            try:
                event = threading.Event()
                def iterator():
                    while True:
                        item = self._transmit_queue.get(event)
                        logging.debug("Streaming send message seq_num=%d",
                                      item.seq_num)
                        yield item

                generator = client.StreamTransmit(iterator())
                for response in generator:
                    if response.status.code == common_pb.STATUS_SUCCESS:
                        self._transmit_queue.confirm(response.next_seq_num)
                        logging.debug("Message with seq_num=%d is "
                            "confirmed", response.next_seq_num-1)
                    elif response.status.code == \
                            common_pb.STATUS_MESSAGE_DUPLICATED:
                        self._transmit_queue.confirm(response.next_seq_num)
                        logging.debug("Resent Message with seq_num=%d is "
                            "confirmed", response.next_seq_num-1)
                    elif response.status.code == \
                            common_pb.STATUS_MESSAGE_MISSING:
                        self._transmit_queue.resend(response.next_seq_num)
                    else:
                        raise RuntimeError("Trainsmit failed with %d" %
                                           response.status.code)
            except Exception as e:  # pylint: disable=broad-except
                if not stop_event.is_set():
                    logging.warning("Bridge streaming broken: %s.", repr(e))
                    metrics.emit_counter('reconnect_counter', 1)
            finally:
                generator.cancel()
                channel.close()
                event.set()
                time.sleep(1)
                self._transmit_queue.resend(-1)
                channel = make_insecure_channel(
                    self._remote_address, ChannelType.REMOTE,
                    options=self._grpc_options, compression=self._compression)
                client = make_ready_client(channel, stop_event)
                self._check_remote_heartbeat(client)

    def _transmit(self, msg):
        assert self._connected, "Cannot transmit before connect"
        metrics.emit_counter('send_counter', 1)
        with self._transmit_send_lock:
            msg.seq_num = self._next_send_seq_num
            self._next_send_seq_num += 1

            if self._streaming_mode:
                self._transmit_queue.put(msg)
                return

            def sender():
                rsp = self._client.Transmit(msg)
                assert rsp.status.code == common_pb.STATUS_SUCCESS, \
                    "Transmit error with code %d."%rsp.status.code
            self._rpc_with_retry(sender, "Bridge transmit failed")


    def _transmit_handler(self, request):
        assert self._connected, "Cannot transmit before connect"
        metrics.emit_counter('receive_counter', 1)
        with self._transmit_receive_lock:
            logging.debug("Received message seq_num=%d."
                          " Wanted seq_num=%d.",
                          request.seq_num, self._next_receive_seq_num)
            if request.seq_num > self._next_receive_seq_num:
                return tws_pb.TrainerWorkerResponse(
                    status=common_pb.Status(
                        code=common_pb.STATUS_MESSAGE_MISSING),
                    next_seq_num=self._next_receive_seq_num)
            if request.seq_num < self._next_receive_seq_num:
                return tws_pb.TrainerWorkerResponse(
                    status=common_pb.Status(
                        code=common_pb.STATUS_MESSAGE_DUPLICATED),
                    next_seq_num=self._next_receive_seq_num)

            # request.seq_num == self._next_receive_seq_num
            self._next_receive_seq_num += 1

            if request.HasField('start'):
                with self._condition:
                    self._received_data[request.start.iter_id] = {}
            elif request.HasField('commit'):
                self._peer_next_iter_id = request.commit.iter_id + 1
            elif request.HasField('data'):
                with self._condition:
                    assert request.data.iter_id in self._received_data
                    self._received_data[
                        request.data.iter_id][
                            request.data.name] = request.data
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
        metrics.emit_counter('load_data_block_counter', 1)
        if self._data_block_handler_fn(request):
            logging.info('Succeeded to load data block %s',
                         request.block_id)
            return common_pb.Status(code=common_pb.STATUS_SUCCESS)
        metrics.emit_counter('load_data_block_fail_counter', 1)
        logging.info('Failed to load data block %s', request.block_id)
        return common_pb.Status(code=common_pb.STATUS_INVALID_DATA_BLOCK)

    def _connect_handler(self, request):
        assert request.app_id == self._app_id, \
            "Connection failed. Application id mismatch: %s vs %s"%(
                request.app_id, self._app_id)
        assert request.worker_rank == self._rank, \
            "Connection failed. Rank mismatch: %s vs %s"%(
                request.worker_rank, self._rank)
        assert len(request.identifier) > 0, \
            "Connection failed. An identifier should be offered!"

        with self._condition:
            if self._connected:
                # If a duplicated reqeust from peer, just ignore it.
                # If a new connect request from peer, suicide.
                if request.identifier != self._peer_identifier:
                    logging.error('Suicide as peer %s has restarted!',
                        request.identifier)
                    os._exit(138)  # Tell Scheduler to restart myself
            else:
                self._peer_identifier = request.identifier
                self._connected = True
                self._connected_at = max(self._connected_at, int(time.time()))
                self._condition.notifyAll()

        return tws_pb.ConnectResponse(
            app_id=self._app_id, worker_rank=self._rank,
            timestamp=self._connected_at)

    def _heartbeat_handler(self, request):
        return tws_pb.HeartbeatResponse(app_id=self._app_id,
                                        worker_rank=self._rank,
                                        current_iter_id=self._current_iter_id)

    def _terminate_handler(self, request):
        with self._condition:
            self._peer_terminated = True
            self._terminated_at = max(self._terminated_at, int(time.time()))
            self._condition.notifyAll()
        return tws_pb.TerminateResponse(
            timestamp=self._terminated_at)

    def _check_remote_heartbeat(self, client):
        try:
            rsp = client.Heartbeat(tws_pb.HeartbeatRequest())
            logging.debug("Heartbeat success: %s:%d at iteration %s.",
                          rsp.app_id, rsp.worker_rank, rsp.current_iter_id)
            return True
        except Exception as e:  # pylint: disable=broad-except
            logging.warning("Heartbeat request failed: %s", repr(e))
            return False

    def _check_iter_timeout(self):
        if self._iter_timeout <= 0:
            return
        with self._condition:
            if not self._current_iter_id:
                return
            duration = time.time() - self._iter_started_at
            if duration > self._iter_timeout:
                msg = 'Suicide as iter run timeout, duration: {}.' \
                    ' maybe blocked in some point.'.format(duration)
                logging.fatal(msg)
                os._exit(138)

    def _supervise_fn(self):
        check_handlers = []
        if self._iter_timeout > 0:
            logging.info('enable supervise iteartion timeout: %f',
                self._iter_timeout)
            check_handlers.append(self._check_iter_timeout)
        if len(check_handlers) == 0:
            return
        while True:
            with self._condition:
                if self._terminated:
                    return
            for handler in check_handlers:
                handler()
            time.sleep(10)

    def connect(self):
        if self._connected:
            logging.warning("Bridge already connected!")
            return

        self._server.start()

        # Get ACK from peer
        msg = tws_pb.ConnectRequest(app_id=self._app_id,
                                    worker_rank=self._rank,
                                    identifier=self._identifier)

        resp = self._rpc_with_retry(
            lambda: self._client.Connect(msg),
            "Bridge failed to connect")
        logging.debug('Has connected to peer.')

        # Ensure REQ from peer
        with self._condition:
            self._connected_at = max(self._connected_at, resp.timestamp)
            while not self._connected:
                self._condition.wait()
        logging.debug('Connected from peer.')

        if self._streaming_mode:
            logging.debug('enter streaming_mode.')
            self._client_daemon = threading.Thread(
                target=self._client_daemon_fn, daemon=True)
            self._client_daemon.start()

        supervise_thread = threading.Thread(
            target=self._supervise_fn, daemon=True)
        supervise_thread.start()

        logging.debug('finish connect.')

    def terminate(self, forced=False):
        with self._condition:
            if not self._connected or self._terminated:
                return
            self._terminated = True

        try:
            if self._client_daemon is not None:
                self._client_daemon_shutdown_fn()
                self._client_daemon.join()
        except Exception as e:  # pylint: disable=broad-except
            logging.warning(
                'Error during streaming shutdown: %s', repr(e))

        # Get ACK from peer
        resp = self._rpc_with_retry(
            lambda: self._client.Terminate(tws_pb.TerminateRequest()),
            "Failed to send terminate message")
        logging.debug('Waiting for peer to terminate.')

        # Ensure REQ from peer
        with self._condition:
            self._terminated_at = max(self._terminated_at, resp.timestamp)
            while not self._peer_terminated:
                self._condition.wait()

        self._server.stop(None)
        logging.debug("Bridge connection terminated")

    @property
    def current_iter_id(self):
        return self._current_iter_id

    def new_iter_id(self):
        iter_id = self._next_iter_id
        self._next_iter_id += 1
        return iter_id

    def start(self, iter_id):
        assert self._current_iter_id is None, "Last iter not finished"
        with self._condition:
            self._iter_started_at = time.time()
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
        logging.debug("sending DataBlock with id %s", block_id)
        stat = self._rpc_with_retry(
            lambda: self._client.LoadDataBlock(msg),
            "Failed to send load data block request")
        if stat.code == common_pb.STATUS_SUCCESS:
            logging.info('Remote succeeded to load data block %s', block_id)
            return True
        logging.info('Remoted failed to load data block %s. code: %d',
                     block_id, stat.code)
        return False

    def register_prefetch_handler(self, func):
        self._prefetch_handlers.append(func)

    def prefetch(self, iter_id, sample_ids):
        msg = tws_pb.TrainerWorkerMessage(prefetch=tws_pb.PrefetchMessage(
            iter_id=iter_id, sample_ids=sample_ids))
        self._transmit(msg)

    def send_proto(self, iter_id, name, proto):
        any_proto = google.protobuf.any_pb2.Any()
        any_proto.Pack(proto)
        msg = tws_pb.TrainerWorkerMessage(data=tws_pb.DataMessage(
            iter_id=iter_id, name=name, any_data=any_proto))
        self._transmit(msg)
        logging.debug('Data: send protobuf %s for iter %d. seq_num=%d.',
                      name, iter_id, msg.seq_num)

    def send(self, iter_id, name, x):
        msg = tws_pb.TrainerWorkerMessage(data=tws_pb.DataMessage(
            iter_id=iter_id, name=name, tensor=tf.make_tensor_proto(x)))
        self._transmit(msg)
        logging.debug('Data: send %s for iter %d. seq_num=%d.',
                      name, iter_id, msg.seq_num)

    def send_op(self, name, x):
        def func(x):
            assert self._current_iter_id is not None, "Bridge not started"
            self.send(self._current_iter_id, name, x.numpy())

        out = tf.py_function(func=func, inp=[x], Tout=[], name='send_' + name)
        return out

    def _receive(self, iter_id, name):
        logging.debug(
            'Data: Waiting to receive %s for iter %d.', name, iter_id)
        start_time = time.time()
        with self._condition:
            while (iter_id not in self._received_data) \
                    or (name not in self._received_data[iter_id]):
                if self._peer_next_iter_id > iter_id:
                    msg = 'Peer committed without sending %s. ' \
                        'Please check model code'%name
                    logging.fatal(msg)
                    raise RuntimeError(msg)
                if not self._condition.wait(10):
                    logging.warning(
                        'Data: Still waiting to receive %s for iter %d...',
                        name, iter_id)
            data = self._received_data[iter_id][name]
        duration = time.time() - start_time
        metrics.emit_timer('receive_timer', duration)
        logging.debug(
            'Data: received %s for iter %d after %f sec.',
            name, iter_id, duration)
        return data

    def receive_proto(self, iter_id, name):
        return self._receive(iter_id, name).any_data

    def receive(self, iter_id, name):
        return tf.make_ndarray(self._receive(iter_id, name).tensor)

    def receive_op(self, name, dtype):
        def func():
            assert self._current_iter_id is not None, "Bridge not started"
            x = self.receive(self._current_iter_id, name)
            return tf.convert_to_tensor(x, dtype=dtype)

        return tf.py_function(func=func, inp=[], Tout=[dtype])[0]

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
            logging.warning('Channel has not been ready for %.2f seconds',
                time.time()-start_time)
            if wait_secs < 5.0:
                wait_secs *= 1.2
        except Exception as e:  # pylint: disable=broad-except
            logging.warning('Waiting channel ready: %s', repr(e))
    return tws_grpc.TrainerWorkerServiceStub(channel)


class Bridge(object):
    class TrainerWorkerServicer(tws_grpc.TrainerWorkerServiceServicer):
        def __init__(self, bridge):
            super(Bridge.TrainerWorkerServicer, self).__init__()
            self._bridge = bridge

        def Transmit(self, request, context):
            return self._bridge._transmit_handler(request)

        @metrics.timer(func_name="one stream transmit", tags={})
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

        self._prefetch_handlers = []
        self._data_block_handler_fn = None

        # Connection related
        self._connected = False
        self._terminated = False
        self._peer_terminated = False
        self._identifier = '%s-%s-%d-%d' % (
            app_id, role, rank, int(time.time())) # Ensure unique per run
        self._peer_identifier = ''

        # data transmit
        self._condition = threading.Condition()
        self._current_iter_id = None
        self._next_iter_id = 0
        self._received_data = {}

        # grpc client
        self._transmit_send_lock = threading.Lock()
        self._grpc_options = [
            ('grpc.max_send_message_length', 2**31-1),
            ('grpc.max_receive_message_length', 2**31-1)
        ]
        self._channel = make_insecure_channel(
            remote_address, ChannelType.REMOTE,
            options=self._grpc_options, compression=self._compression)
        self._client = tws_grpc.TrainerWorkerServiceStub(self._channel)
        self._next_send_seq_num = 0
        self._transmit_queue = queue.Queue()
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

    def _client_daemon_fn(self):
        stop_event = threading.Event()
        generator = None
        channel = make_insecure_channel(
            self._remote_address, ChannelType.REMOTE,
            options=self._grpc_options, compression=self._compression)
        client = make_ready_client(channel, stop_event)

        lock = threading.Lock()
        resend_list = collections.deque()
        metrics_list = collections.deque()
        metrics_sum_resend_seq = 0

        @metrics.timer(func_name="shutdown_fn", tags={})
        def shutdown_fn():
            with lock:
                while len(resend_list) > 0 or not self._transmit_queue.empty():
                    logging.debug(
                        "Waiting for resend queue's being cleaned. "
                        "Resend queue size: %d", len(resend_list))
                    lock.release()
                    time.sleep(1)
                    lock.acquire()

            stop_event.set()
            if generator is not None:
                generator.cancel()

        self._client_daemon_shutdown_fn = shutdown_fn

        while not stop_event.is_set():
            try:
                def iterator():
                    with lock:
                        resend_msgs = list(resend_list)
                    for item in resend_msgs:
                        logging.warning("Streaming resend message seq_num=%d",
                                        item.seq_num)
                        metrics.emit_store(name="resend_msg_seq_num",
                                           value=int(item.seq_num),
                                           tags={})
                        while metrics_list and item.seq_num - metrics_list[0] >= 100:
                            metrics_list.popleft()
                            metrics_sum_resend_seq -= 1
                        if metrics_list and metrics_list[len(metrics_list)-1] < item.seq_num:
                            metrics_list.append(item.seq_num)
                            metrics_sum_resend_seq += 1
                        metrics.emit_store(name="rate_of_resend",
                                           value=float(metrics_sum_resend_seq/100),
                                           tags={})
                        yield item
                    while True:
                        item = self._transmit_queue.get()
                        with lock:
                            resend_list.append(item)
                        logging.debug("Streaming send message seq_num=%d",
                                      item.seq_num)
                        metrics.emit_store(name="send_msg_seq_num",
                                           value=int(item.seq_num),
                                           tags={})
                        yield item

                metrics.emit_store(name="rate_of_resend",
                                   value=float(metrics_sum_resend_seq/100),
                                   tags={})
                time_start = time.time()
                generator = client.StreamTransmit(iterator())
                time_end = time.time()
                metrics.emit_timer(name="one_StreamTransmit_spend",
                                   value=int(time_end-time_start),
                                   tags={})
                for response in generator:
                    if response.status.code == common_pb.STATUS_SUCCESS:
                        logging.debug("Message with seq_num=%d is "
                            "confirmed", response.next_seq_num-1)
                    elif response.status.code == \
                        common_pb.STATUS_MESSAGE_DUPLICATED:
                        logging.debug("Resent Message with seq_num=%d is "
                            "confirmed", response.next_seq_num-1)
                    elif response.status.code == \
                        common_pb.STATUS_MESSAGE_MISSING:
                        raise RuntimeError("Message with seq_num=%d is "
                            "missing!" % (response.next_seq_num-1))
                    else:
                        raise RuntimeError("Trainsmit failed with %d" %
                                           response.status.code)
                    with lock:
                        while resend_list and \
                                resend_list[0].seq_num < response.next_seq_num:
                            resend_list.popleft()
                        min_seq_num_to_resend = resend_list[0].seq_num \
                            if resend_list else "NaN"
                        logging.debug(
                            "Resend queue size: %d, starting from seq_num=%s",
                            len(resend_list), min_seq_num_to_resend)
            except Exception as e:  # pylint: disable=broad-except
                if not stop_event.is_set():
                    logging.warning("Bridge streaming broken: %s.", repr(e))
            finally:
                generator.cancel()
                channel.close()
                logging.warning(
                    "Restarting streaming: resend queue size: %d, "
                    "starting from seq_num=%s", len(resend_list),
                    resend_list and resend_list[0].seq_num or "NaN")
                channel = make_insecure_channel(
                    self._remote_address, ChannelType.REMOTE,
                    options=self._grpc_options, compression=self._compression)
                client = make_ready_client(channel, stop_event)
                self._check_remote_heartbeat()

    def _transmit(self, msg):
        assert self._connected, "Cannot transmit before connect"
        with self._transmit_send_lock:
            msg.seq_num = self._next_send_seq_num
            self._next_send_seq_num += 1

            if self._streaming_mode:
                self._transmit_queue.put(msg)
                return

            while True:
                try:
                    rsp = self._client.Transmit(msg)
                    assert rsp.status.code == common_pb.STATUS_SUCCESS, \
                        "Transmit error with code %d."%rsp.status.code
                    break
                except Exception as e:  # pylint: disable=broad-except
                    logging.warning("Bridge transmit failed: %s. " \
                                    "Retry in 1 second...", repr(e))
                    self._channel.close()
                    time.sleep(1)
                    self._channel = make_insecure_channel(
                        self._remote_address, ChannelType.REMOTE,
                        options=self._grpc_options,
                        compression=self._compression)
                    self._client = make_ready_client(self._channel)
                    self._check_remote_heartbeat()

    def _transmit_handler(self, request):
        assert self._connected, "Cannot transmit before connect"
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
                pass
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

    @metrics.timer(func_name="data_block_req", tags={})
    def _data_block_handler(self, request):
        assert self._connected, "Cannot load data before connect"
        if not self._data_block_handler_fn:
            raise RuntimeError("Received DataBlockMessage but" \
                                " no handler registered")
        self._data_block_handler_fn(request)
        return common_pb.Status(code=common_pb.STATUS_SUCCESS)

    @metrics.timer(func_name="connect_req", tags={})
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
                self._condition.notifyAll()

        return tws_pb.ConnectResponse(app_id=self._app_id,
                                      worker_rank=self._rank)

    def _heartbeat_handler(self, request):
        return tws_pb.HeartbeatResponse(app_id=self._app_id,
                                        worker_rank=self._rank,
                                        current_iter_id=self._current_iter_id)

    def _terminate_handler(self, request):
        with self._condition:
            self._peer_terminated = True
            self._condition.notifyAll()
        return tws_pb.TerminateResponse()

    def _check_remote_heartbeat(self):
        try:
            rsp = self._client.Heartbeat(tws_pb.HeartbeatRequest())
            logging.debug("Heartbeat success: %s:%d at iteration %s.",
                          rsp.app_id, rsp.worker_rank, rsp.current_iter_id)
            return True
        except Exception as e:  # pylint: disable=broad-except
            logging.warning("Heartbeat request failed: %s", repr(e))
            return False

    @metrics.timer(func_name="connect", tags={})
    def connect(self):
        if self._connected:
            logging.warning("Bridge already connected!")
            return

        self._server.start()

        # Get ACK from peer
        msg = tws_pb.ConnectRequest(app_id=self._app_id,
                                    worker_rank=self._rank,
                                    identifier=self._identifier)
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
        logging.debug('Has connected to peer.')

        # Ensure REQ from peer
        with self._condition:
            while not self._connected:
                self._condition.wait()
        logging.debug('Connected from peer.')

        if self._streaming_mode:
            logging.debug('enter streaming_mode.')
            self._client_daemon = threading.Thread(
                target=self._client_daemon_fn)
            self._client_daemon.start()
        logging.debug('finish connect.')

    @metrics.timer(func_name="terminate", tags={})
    def terminate(self, forced=False):
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
        while True:
            try:
                self._client.Terminate(tws_pb.TerminateRequest())
                break
            except Exception as e:  # pylint: disable=broad-except
                logging.warning(
                    "Failed to send terminate message: %s. " \
                    "Retry in 1 second...", repr(e))
                time.sleep(1)
                continue
        logging.debug('Waiting for peer to terminate.')

        # Ensure REQ from peer
        with self._condition:
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
        return self._client.LoadDataBlock(msg)

    def register_prefetch_handler(self, func):
        self._prefetch_handlers.append(func)

    def prefetch(self, iter_id, sample_ids):
        msg = tws_pb.TrainerWorkerMessage(prefetch=tws_pb.PrefetchMessage(
            iter_id=iter_id, sample_ids=sample_ids))
        self._transmit(msg)

    @metrics.timer(func_name="send proto", tags={})
    def send_proto(self, iter_id, name, proto):
        any_proto = google.protobuf.any_pb2.Any()
        any_proto.Pack(proto)
        msg = tws_pb.TrainerWorkerMessage(data=tws_pb.DataMessage(
            iter_id=iter_id, name=name, any_data=any_proto))
        self._transmit(msg)
        logging.debug('Data: send protobuf %s for iter %d. seq_num=%d.',
                      name, iter_id, msg.seq_num)

    @metrics.timer(func_name="send", tags={})
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

    @metrics.timer(func_name="receive proto", tags={})
    def receive_proto(self, iter_id, name):
        logging.debug('Data: Waiting to receive proto %s for iter %d.',
                      name, iter_id)
        with self._condition:
            while (iter_id not in self._received_data) \
                    or (name not in self._received_data[iter_id]):
                self._condition.wait()
            data = self._received_data[iter_id][name]
        logging.debug('Data: received %s for iter %d.', name, iter_id)
        return data.any_data

    @metrics.timer(func_name="receive", tags={})
    def receive(self, iter_id, name):
        logging.debug('Data: Waiting to receive %s for iter %d.', name,
                      iter_id)
        with self._condition:
            while (iter_id not in self._received_data) \
                    or (name not in self._received_data[iter_id]):
                self._condition.wait()
            data = self._received_data[iter_id][name]
        logging.debug('Data: received %s for iter %d.', name, iter_id)
        return tf.make_ndarray(data.tensor)

    def receive_op(self, name, dtype):
        def func():
            assert self._current_iter_id is not None, "Bridge not started"
            x = self.receive(self._current_iter_id, name)
            return tf.convert_to_tensor(x, dtype=dtype)

        return tf.py_function(func=func, inp=[], Tout=[dtype])[0]

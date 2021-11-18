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
import threading
import time
from distutils.util import strtobool

import tensorflow.compat.v1 as tf
from google.protobuf import any_pb2 as any_pb
from fedlearner.common import fl_logging, common
from fedlearner.channel import Channel
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import trainer_worker_service_pb2 as tws2_pb
from fedlearner.common import trainer_worker_service_pb2_grpc as tws2_grpc
from fedlearner.trainer._global_context import global_context as _gctx

_BRIDGE_SUPERVISE_ENABLED = strtobool(
    os.getenv("FL_BRIDGE_SUPERVISE_ENABLED", "false"))

class Bridge(object):
    class TrainerWorkerServicer(tws2_grpc.TrainerWorkerServiceServicer):
        def __init__(self, bridge):
            super(Bridge.TrainerWorkerServicer, self).__init__()
            self._bridge = bridge

        def Transmit(self, request_iterator, context):
            for request in request_iterator:
                yield self._bridge._transmit_handler(request)

        def LoadDataBlock(self, request, context):
            return self._bridge._data_block_handler(request)

    def __init__(self,
                 role,
                 listen_port,
                 remote_address,
                 app_id=None,
                 worker_rank=0,
                 stream_queue_size=1024,
                 waiting_alert_timeout=10):
        self._role = role
        self._listen_address = "[::]:{}".format(listen_port)
        self._remote_address = remote_address
        if app_id is None:
            app_id = 'test_trainer'
        self._worker_rank = worker_rank
        self._token = "{}-{}".format(app_id, worker_rank)

        self._condition = threading.Condition()
        self._connected = False
        self._terminated = False
        self._peer_terminated = False

        self._current_iter_id = None
        self._next_iter_id = 0
        self._iter_started_at = 0
        self._peer_start_iter_id = None
        self._peer_commit_iter_id = None

        self._received_data = collections.defaultdict(dict)
        self._data_block_handler_fn = None

        self._waiting_alert_timeout = waiting_alert_timeout
        if self._waiting_alert_timeout < 1:
            self._waiting_alert_timeout = 1

        # transmit stream queue
        self._stream_queue = collections.deque()
        self._stream_queue_size = stream_queue_size
        self._stream_thread = None
        self._stream_condition = threading.Condition()
        self._stream_terminated = False

        # channel
        self._channel = Channel(
            self._listen_address, self._remote_address,
            token=self._token,
            max_workers=common.get_tf_config()["grpc_server_channel_threads"],
            stats_client=_gctx.stats_client)
        self._channel.subscribe(self._channel_callback)

        # client & server
        self._client = tws2_grpc.TrainerWorkerServiceStub(self._channel)
        tws2_grpc.add_TrainerWorkerServiceServicer_to_server(
            Bridge.TrainerWorkerServicer(self), self._channel)

        # supervise
        self._supervise_interval = 5
        self._supervise_iteration_timeout = 1200


    def _channel_callback(self, channel, event):
        if event == Channel.Event.PEER_CLOSED:
            with self._condition:
                self._peer_terminated = True
                self._condition.notify_all()
        if event == Channel.Event.ERROR:
            err = channel.error()
            fl_logging.fatal("[Bridge] suicide as channel exception: %s, "
                             "maybe caused by peer restart", repr(err))
            os._exit(138)  # Tell Scheduler to restart myself

    @property
    def current_iter_id(self):
        return self._current_iter_id

    @property
    def next_iter_id(self):
        return self._next_iter_id

    @property
    def role(self):
        return self._role

    @property
    def worker_rank(self):
        return self._worker_rank

    @property
    def connected_at(self):
        return self._channel.connected_at

    @property
    def terminated_at(self):
        return self._channel.closed_at

    def _check_iteration_timeout(self):
        with self._condition:
            if self._current_iter_id is None:
                return
            duration = time.time() - self._iter_started_at
            if duration >= self._supervise_iteration_timeout:
                msg = "Suicide as iter run timeout, duration: {}, " \
                      "maybe blocked in some point.".format(duration)
                fl_logging.fatal(msg)
                os._exit(138)

    def _supervise_fn(self):
        check_handlers = []
        if self._supervise_iteration_timeout > 0:
            fl_logging.info("enable supervise iteartion timeout: %f",
                            self._supervise_iteration_timeout)
            check_handlers.append(self._check_iteration_timeout)
        if len(check_handlers) == 0:
            return
        while True:
            with self._condition:
                if self._terminated:
                    return
            for handler in check_handlers:
                handler()
            time.sleep(self._supervise_interval)

    def connect(self):
        with self._condition:
            if self._connected:
                return
            self._connected = True
            self._channel.connect()
        self._stream_transmit_thread = threading.Thread(
            target=self._stream_transmit_fn)
        self._stream_transmit_thread.daemon = True
        self._stream_transmit_thread.start()
        if _BRIDGE_SUPERVISE_ENABLED:
            self._supervise_thread = threading.Thread(
                target=self._supervise_fn)
            self._supervise_thread.daemon = True
            self._supervise_thread.start()

    def terminate(self):
        with self._condition:
            if not self._connected:
                return
            if self._terminated:
                return

            if self._is_iter_started:
                self.commit()

            self._terminated = True
            self._condition.notify_all()
            with self._stream_condition:
                self._stream_terminated = True
                self._stream_condition.notify_all()
        self._stream_transmit_thread.join()
        self._channel.close()

    def _stream_transmit_fn(self):
        IDLE_TIMEOUT = 30
        fl_logging.debug("[Bridge] stream transmit started")

        def request_iterator():
            fl_logging.debug("[Bridge] stream transmitting")
            while True:
                with self._stream_condition:
                    if len(self._stream_queue) == 0:
                        start = time.time()
                        while len(self._stream_queue) == 0:
                            duration = time.time() - start
                            if self._stream_terminated:
                                return
                            if duration >= IDLE_TIMEOUT:
                                fl_logging.debug("[Bridge] stream transmit "
                                   " closed by idle timeout: %f sec",
                                   IDLE_TIMEOUT)
                                return
                            self._stream_condition.wait(IDLE_TIMEOUT-duration)
                    msg = self._stream_queue.popleft()
                    self._stream_condition.notify_all()
                yield msg

        while True:
            with self._stream_condition:
                while len(self._stream_queue) == 0:
                    if self._stream_terminated:
                        fl_logging.debug("[Bridge] stream transmit closed")
                        return
                    self._stream_condition.wait()
            response_iterator = \
                self._client.Transmit(request_iterator())
            for _ in response_iterator:
                pass

    def _transmit(self, msg):
        with self._stream_condition:
            assert not self._stream_terminated
            while len(self._stream_queue) == self._stream_queue_size:
                fl_logging.warning("[Bridge] transmit stream queue is full, "
                                   "size: %d", len(self._stream_queue))
                self._stream_condition.wait()
            self._stream_queue.append(msg)
            self._stream_condition.notify_all()

    def _transmit_handler(self, request):
        with self._condition:
            if request.HasField("start"):
                if self._peer_commit_iter_id is not None \
                    and request.start.iter_id <= self._peer_commit_iter_id:
                    fl_logging.warning(
                        "[Bridge] received peer start iter_id: %d "
                        "which has been committed. "
                        "maybe caused by resend.(peer_commit_iter_id: %d)",
                        request.start.iter_id, self._peer_commit_iter_id)
                elif self._peer_start_iter_id is not None:
                    fl_logging.warning(
                        "[Bridge] received repeated peer start iter_id: %d. "
                        "maybe caused by resend.(peer_start_iter_id: %d)",
                        request.start.iter_id, self._peer_start_iter_id)
                else:
                    fl_logging.debug("[Bridge] received peer start iter_id: %d",
                                     request.start.iter_id)
                    self._peer_start_iter_id = request.start.iter_id
                    self._condition.notify_all()

            elif request.HasField("data"):
                if self._peer_start_iter_id is None:
                    fl_logging.warning(
                        "[Bridge] received data iter_id: %d without start. "
                        "maybe caused by resend.",
                        request.data.iter_id)
                elif self._peer_start_iter_id != request.data.iter_id:
                    fl_logging.warning(
                        "[Bridge] received data iter_id: %d no match start. "
                        "maybe caused by resend.(peer_start_iter_id: %d)",
                        request.data.iter_id, self._peer_start_iter_id)
                else:
                    iter_id = self._current_iter_id \
                        if self._current_iter_id is not None \
                            else self._next_iter_id
                    if request.data.iter_id < iter_id:
                        fl_logging.debug("[Bridge] received data iter_id: %d, "
                            "name: %s, ignored by our commit."
                            "(current_iter_id: %s, next_iter_id: %d)",
                            request.data.iter_id, request.data.name,
                            self._current_iter_id, self._next_iter_id)
                    else:
                        fl_logging.debug("[Bridge] received data iter_id: %d, "
                            "name: %s",
                            request.data.iter_id, request.data.name)
                        self._received_data[ \
                            request.data.iter_id][ \
                                request.data.name] = request.data
                        self._condition.notify_all()

            elif request.HasField("commit"):
                if self._peer_commit_iter_id is not None \
                    and request.commit.iter_id <= self._peer_commit_iter_id:
                    fl_logging.warning(
                        "[Bridge] receive repeated peer commit iter_id: %d. "
                        "maybe caused by resend.(peer_commit_iter_id: %d)",
                        request.commit.iter_id, self._peer_commit_iter_id)
                elif self._peer_start_iter_id is None:
                    fl_logging.error(
                        "[Bridge] receive peer commit iter_id: %d "
                        "without start",
                        request.commit.iter_id)
                    # return error?
                elif request.commit.iter_id != self._peer_start_iter_id:
                    fl_logging.error(
                        "[Bridge] receive peer commit iter_id: %s "
                        "no match start.(peer_start_iter_id: %d)",
                        request.commit.iter_id, self._peer_start_iter_id)
                    # return error?
                else:
                    fl_logging.debug("[Bridge] receive peer commit iter_id: %d",
                        request.commit.iter_id)
                    self._peer_start_iter_id = None
                    self._peer_commit_iter_id = request.commit.iter_id
                    self._condition.notify_all()

        return tws2_pb.TransmitResponse(
            status=common_pb.Status(code=common_pb.STATUS_SUCCESS))

    def _data_block_handler(self, request):
        assert self._data_block_handler_fn is not None, \
            "[Bridge] receive DataBlockMessage but no handler registered."
        if self._data_block_handler_fn(request):
            fl_logging.info("[Bridge] succeeded to load data block %s",
                         request.block_id)
            return tws2_pb.LoadDataBlockResponse(
                status=common_pb.Status(code=common_pb.STATUS_SUCCESS)
            )
        fl_logging.info("[Bridge] failed to load data block %s",
                        request.block_id)
        return tws2_pb.LoadDataBlockResponse(
            status=common_pb.Status(code=common_pb.STATUS_INVALID_DATA_BLOCK)
        )

    @property
    def _is_iter_started(self):
        return self._current_iter_id is not None

    @property
    def _is_iter_committed(self):
        return self._current_iter_id is None

    def _assert_ready(self):
        if not self._connected:
            raise RuntimeError("[Bridge] not connected yet")
        if self._terminated:
            raise RuntimeError("[Bridge] has been terminated")

    def _assert_iter_started(self):
        self._assert_ready()
        if not self._is_iter_started:
            raise RuntimeError("[Bridge] not started yet")

    def _assert_iter_committed(self):
        self._assert_ready()
        if not self._is_iter_committed:
            raise RuntimeError("[Bridge] last started not commit yet")

    def start(self):
        with self._condition:
            self._assert_iter_committed()

            self._current_iter_id = self._next_iter_id
            self._next_iter_id += 1
            self._iter_started_at = time.time()
            self._transmit(tws2_pb.TransmitRequest(
                start=tws2_pb.TransmitRequest.StartMessage(
                    iter_id=self._current_iter_id)
            ))
            fl_logging.debug("[Bridge] send start iter_id: %d",
                self._current_iter_id)

    def commit(self):
        with self._condition:
            self._assert_iter_started()

            self._transmit(tws2_pb.TransmitRequest(
                commit=tws2_pb.TransmitRequest.CommitMessage(
                    iter_id=self._current_iter_id)
            ))
            fl_logging.debug("[Bridge] send commit iter_id: %d",
                self._current_iter_id)
            # delete committed data
            if self._current_iter_id in self._received_data:
                del self._received_data[self._current_iter_id]
            iter_id = self._current_iter_id
            duration = (time.time() - self._iter_started_at) * 1000
            self._current_iter_id = None

        with _gctx.stats_client.pipeline() as pipe:
            pipe.gauge("trainer.bridge.iterator_step", iter_id)
            pipe.timing("trainer.bridge.iterator_timing", duration)

    def register_data_block_handler(self, func):
        assert self._data_block_handler_fn is None, \
            "[Bridge] DataBlock handler already registered"
        self._data_block_handler_fn = func

    def load_data_block(self, count, block_id):
        req = tws2_pb.LoadDataBlockRequest(count=count, block_id=block_id)
        fl_logging.debug("[Bridge] sending DataBlock with id %s", block_id)
        resp = self._client.LoadDataBlock(req)
        if resp.status.code == common_pb.STATUS_SUCCESS:
            fl_logging.info("[Bridge] remote succeeded to load data block %s",
                            block_id)
            return True
        fl_logging.warning("[Bridge] remoted failed to load data block %s. "
                           "code: %d", block_id, resp.status.code)
        return False

    def _send(self, name, tensor=None, any_data=None):
        with self._condition:
            self._assert_iter_started()

            self._transmit(tws2_pb.TransmitRequest(
                data=tws2_pb.TransmitRequest.DataMessage(
                    iter_id=self._current_iter_id,
                    name=name,
                    tensor=tensor,
                    any_data=any_data,
                )))
            fl_logging.debug("[Bridge] Data: send iter_id: %d, name: %s",
                self._current_iter_id, name)

    def send(self, name, x):
        self._send(name, tensor=tf.make_tensor_proto(x))

    def send_proto(self, name, proto):
        any_proto = any_pb.Any()
        any_proto.Pack(proto)
        self._send(name, any_data=any_proto)

    def send_op(self, name, x):
        def func(x):
            self.send(name, x)

        return tf.py_function(func=func, inp=[x], Tout=[], name='send_'+name)

    def _receive(self, name):
        start_time = time.time()
        alert_count = 0
        with self._condition:
            self._assert_iter_started()
            iter_id = self._current_iter_id
            while (iter_id not in self._received_data
                   or name not in self._received_data[iter_id]):
                self._assert_iter_started()
                if iter_id != self._current_iter_id:
                    raise RuntimeError(
                        "[Bridge] iter change while waiting receive data, "
                        "iter_id: {}, name: {}".format(iter_id, name))
                if self._peer_commit_iter_id is not None \
                    and iter_id <= self._peer_commit_iter_id:
                    raise RuntimeError(
                        "[Bridge] peer committed without sending data "
                        "iter_id: {}, name: {}".format(iter_id, name))
                if self._peer_terminated:
                    raise RuntimeError(
                        "[Bridge] peer terminated without sending data "
                        "iter_id: {}, name: {}".format(iter_id, name))
                duration = time.time() - start_time
                if duration >= (alert_count+1)*self._waiting_alert_timeout:
                    alert_count += 1
                    fl_logging.warning("[Bridge] Data: waiting to receive "
                        "iter_id: %d, name: %s timeout. duration: %f sec",
                        iter_id, name, duration)
                wait_timeout = self._waiting_alert_timeout - \
                    (duration % self._waiting_alert_timeout)
                self._condition.wait(wait_timeout)
            data = self._received_data[iter_id][name]

        duration = time.time() - start_time
        _gctx.stats_client.timing(
            "trainer.bridge.receive_timing", duration * 1000,
            {"bridge_receive_name": name}
        )
        fl_logging.debug("[Bridge] Data: received iter_id: %d, name: %s "
                         "after %f sec",
                         iter_id, name, duration)
        return data

    def receive(self, name):
        return tf.make_ndarray(self._receive(name).tensor)

    def receive_proto(self, name):
        return self._receive(name).any_data

    def receive_op(self, name, dtype):
        def func():
            return tf.convert_to_tensor(self.receive(name), dtype=dtype)

        return tf.py_function(func=func, inp=[], Tout=dtype, name='recv_'+name)

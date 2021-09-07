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

import os
import signal
import time
from concurrent import futures
import threading
import grpc

import tensorflow.compat.v1 as tf
from fedlearner.common import fl_logging
from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.common import trainer_master_service_pb2_grpc as tm_grpc
from fedlearner.common import common_pb2 as common_pb
from fedlearner.trainer.estimator import FLEstimator
from fedlearner.trainer.sparse_estimator import SparseFLEstimator
from fedlearner.trainer.cluster_server import ClusterServer
from fedlearner.trainer._global_context import global_context as _gctx


class ExportModelHook():
    def after_save(self, sess, model, export_dir, inputs, outputs):
        pass


class _TriggerHook(tf.train.SessionRunHook):
    def __init__(self,
                 trigger_secs=None,
                 trigger_steps=None,
                 trigger_fn=None):
        self._trigger_secs = trigger_secs
        self._trigger_steps = trigger_steps
        self._trigger_fn = trigger_fn

    def begin(self):
        self._global_step_tensor = tf.train.get_or_create_global_step()
        self._last_triggered_time = None
        self._last_triggered_step = None

    def after_create_session(self, session, coord):
        global_step = session.run(self._global_step_tensor)
        self._trigger(global_step)

    def after_run(self, run_context, run_values):
        global_step = run_context.session.run(self._global_step_tensor)
        if self._should_trigger(global_step):
            self._trigger(global_step)

    def end(self, session):
        global_step = session.run(self._global_step_tensor)
        self._trigger(global_step)

    def _should_trigger(self, global_step):
        if self._last_triggered_time is None \
            or self._last_triggered_step is None:
            return True

        if self._trigger_secs is not None:
            if time.time() >= self._last_triggered_time + self._trigger_secs:
                return True

        if self._trigger_steps is not None:
            if global_step >= self._last_triggered_step + self._trigger_steps:
                return True

        return False

    def _trigger(self, global_step):
        if self._trigger_fn:
            self._trigger_fn(global_step)
        self._last_triggered_time = time.time()
        self._last_triggered_step = global_step


#class _CheckpointSaverHook(tf.train.CheckpointSaverHook):
#    def _save(self, session, step):
#        if self._timer.last_triggered_step() is None:
#            # skip save checkpoint
#            fl_logging.info("skip save checkpoint")
#            return False
#        return super(_CheckpointSaverHook, self)._save(session, step)


class _DataVisitorCheckpointHook(tf.train.SessionRunHook):
    def __init__(self, visitor):
        self._visitor = visitor

    def begin(self):
        self._ckpt_plhd = tf.placeholder(tf.string, name="data_checkpoint_plhd")
        self._ckpt_var = tf.Variable("", name="data_checkpoint")
        self._save_op = self._ckpt_var.assign(self._ckpt_plhd)

    def after_create_session(self, session, coord):
        data = session.run(self._ckpt_var)
        self._visitor.restore(data)

    def before_checkpoint_save(self, session, global_step_value):
        data = self._visitor.dump()
        fl_logging.info("DataVisitor save checkpoint for global step %d, "
                        "size: %d", global_step_value, len(data))
        session.run(
            self._save_op,
            {self._ckpt_plhd: data},
        )

    def create_checkpoint_saver_listener(self):
        return _DataVisitorCheckpointHook.CheckpointSaverListener(self)

    class CheckpointSaverListener(tf.train.CheckpointSaverListener):
        def __init__(self, hook):
            self._hook = hook
        def before_save(self, session, global_step_value):
            self._hook.before_checkpoint_save(session, global_step_value)


class DataBlockCheckpointSaverListener(tf.train.CheckpointSaverListener):
    def __init__(self, visitor):
        self._visitor = visitor

    def begin(self):
        self._ckpt = tf.placeholder(tf.string, name="data_checkpoint_plhd")
        var_tmp = tf.Variable("", name="data_checkpoint")
        self._save_op = var_tmp.assign(self._ckpt)

    def before_save(self, session, global_step_value):
        session.run(
            self._save_op,
            {self._ckpt: self._visitor.dump()}
        )
        #fl_logging.info("data checkpoint saved result: %s", res)


class _FakeBridge():
    def send_op(self, name, x):
        def func(x):
            raise RuntimeError("Unexcepted call send op")

        out = tf.py_function(func=func, inp=[x], Tout=[], name='send_' + name)
        return out
    def receive_op(self, name, dtype):
        def func():
            raise RuntimeError("Unexcepted call receive op")

        return tf.py_function(func=func, inp=[], Tout=[dtype])[0]
    def register_data_block_handler(self, handler):
        pass


class _FakeTrainerMasterClient():
    pass


class _TrainerMaster(tm_grpc.TrainerMasterServiceServicer):
    def __init__(self,
                 cluster_server,
                 role,
                 mode,
                 model_fn,
                 input_fn,
                 serving_input_receiver_fn,
                 checkpoint_filename_with_path=None,
                 checkpoint_path=None,
                 save_checkpoint_steps=None,
                 save_checkpoint_secs=None,
                 summary_path=None,
                 summary_save_steps=None,
                 summary_save_secs=None,
                 export_path=None,
                 sparse_estimator=False,
                 export_model_hook=None):
        self._cluster_server = cluster_server
        self._role = role
        self._mode = mode
        self._model_fn = model_fn
        self._input_fn = input_fn
        self._serving_input_receiver_fn = serving_input_receiver_fn
        self._checkpoint_filename_with_path = checkpoint_filename_with_path
        self._checkpoint_path = checkpoint_path
        self._save_checkpoint_steps = save_checkpoint_steps
        self._save_checkpoint_secs = save_checkpoint_secs
        self._summary_path = summary_path
        self._summary_save_steps = summary_save_steps
        self._summary_save_secs = summary_save_secs
        self._export_path = export_path
        self._sparse_estimator = sparse_estimator
        self._export_model_hook = export_model_hook

        self._lock = threading.RLock()
        self._status = tm_pb.MasterStatus.CREATED
        self._checkpoint_listeners = []
        self._session_hooks = []

        self._running_workers = set() # set(worker_rank)
        self._completed_workers = set() # set(worker_rank)

        # for compatibility
        self._worker0_terminated_at = 0
        self._worker0_cluster_def = None

    def _check_status(self, callback_fn):
        with self._lock:
            return callback_fn(self._status)

    def _run_grpc_server(self, address):
        self._grpc_server = grpc.server(
            futures.ThreadPoolExecutor(
                max_workers=8,
                thread_name_prefix="TrainerMasterServerThreadPoolExecutor"
            ))
        tm_grpc.add_TrainerMasterServiceServicer_to_server(
            self, self._grpc_server)
        self._grpc_server.add_insecure_port(address)
        self._grpc_server.start()
        fl_logging.info('Trainer Master Server start on address: %s', address)

    def _transfer_status(self, frm, to):
        if self._status != frm:
            raise RuntimeError(
                "Trainer Master status transfer failed, "
                "want from %s to %s, but current status: %s"% \
                            (tm_pb.MasterStatus.Name(frm),
                             tm_pb.MasterStatus.Name(to),
                             tm_pb.MasterStatus.Name(self._status))
                )
        self._status = to
        fl_logging.info("Trainer Master status transfer, from %s to %s",
                        tm_pb.MasterStatus.Name(frm),
                        tm_pb.MasterStatus.Name(to))

    def run_forever(self, listen_port=None):
        with self._lock:
            self._transfer_status(tm_pb.MasterStatus.CREATED,
                                  tm_pb.MasterStatus.INITIALING)

        if listen_port:
            self._run_grpc_server(listen_port)

        while self._cluster_server is None:
            # waiting receive cluster_def from worker0
            with self._lock:
                if self._worker0_cluster_def:
                    fl_logging.info("received worker_0 cluster_def: %s",
                                    self._worker0_cluster_def)
                    self._cluster_server = ClusterServer(
                        tf.train.ClusterSpec(self._worker0_cluster_def),
                        "master")
                    break
            fl_logging.info("still waiting receive cluster_def from worker_0")
            time.sleep(2)

        self._run()

        sig = signal.sigwait([signal.SIGHUP, signal.SIGINT, signal.SIGTERM])
        fl_logging.info("Server shutdown by signal: %s",
                        signal.Signals(sig).name)

    def _add_checkpoint_listener(self, listener):
        with self._lock:
            self._checkpoint_listeners.append(listener)

    def _add_session_hook(self, hook):
        with self._lock:
            self._session_hooks.append(hook)

    def _create_estimator(self):
        estimator_factory = SparseFLEstimator \
            if self._sparse_estimator else FLEstimator
        return estimator_factory(
            cluster_server=self._cluster_server,
            bridge=_FakeBridge(),
            trainer_master=_FakeTrainerMasterClient(),
            role=self._role,
            model_fn=self._model_fn)

    def _run(self):
        fl_logging.info("create estimator")
        estimator = self._create_estimator()
        fl_logging.info("start session_run")
        self._session_run(estimator)
        fl_logging.info("session_run done")
        fl_logging.info("start export_model")
        self._export_model(estimator)
        fl_logging.info("export_model done")
        self._transfer_status(tm_pb.MasterStatus.WORKER_COMPLETED,
                              tm_pb.MasterStatus.COMPLETED)

    def _session_run(self, estimator):
        mode_key = tf.estimator.ModeKeys.TRAIN if self._mode == "train" \
                       else tf.estimator.ModeKeys.EVAL
        with tf.Graph().as_default() as g, \
            g.device(self._cluster_server.device_setter):

            features, labels = estimator. \
                _get_features_and_labels_from_input_fn(
                    self._input_fn, mode_key)
            # only for create graph
            spec, _ = estimator._get_model_spec(
                features, labels, mode_key)

            session_creator = tf.train.ChiefSessionCreator(
                master=self._cluster_server.target,
                config=self._cluster_server.cluster_config,
                checkpoint_filename_with_path= \
                    self._checkpoint_filename_with_path
            )

            hooks = self._session_hooks

            # saver hook
            if mode_key == tf.estimator.ModeKeys.TRAIN \
                and self._checkpoint_path \
                and (self._save_checkpoint_secs \
                    or self._save_checkpoint_steps):
                hooks.append(
                    tf.train.CheckpointSaverHook(
                        checkpoint_dir=self._checkpoint_path,
                        save_secs=self._save_checkpoint_secs,
                        save_steps=self._save_checkpoint_steps,
                        listeners=self._checkpoint_listeners,
                    )
                )

            # summary hook
            if mode_key == tf.estimator.ModeKeys.TRAIN \
                and (self._summary_save_secs or self._summary_save_steps):
                if not self._summary_path:
                    self._summary_path = self._checkpoint_path
                if self._summary_path:
                    hooks.append(
                        tf.train.SummarySaverHook(
                            output_dir=self._summary_path,
                            save_secs=self._summary_save_secs,
                            save_steps=self._summary_save_steps,
                            scaffold=session_creator._scaffold,
                        )
                    )
            noop = tf.no_op()
            with tf.train.MonitoredSession(
                session_creator=session_creator,
                hooks=hooks) as sess:

                with self._lock:
                    # ready, set status to running
                    self._transfer_status(tm_pb.MasterStatus.INITIALING,
                                          tm_pb.MasterStatus.RUNNING)

                while True:
                    sess.run(noop)
                    with self._lock:
                        if self._status == tm_pb.MasterStatus.WORKER_COMPLETED:
                            break
                    time.sleep(0.2)


    def _export_model(self, estimator):
        if self._export_path:
            export_path = os.path.join(
                self._export_path, str(self._worker0_terminated_at))
            with tf.Graph().as_default() as g, \
                g.device(self._cluster_server.device_setter):

                receiver = self._serving_input_receiver_fn()
                spec, model = estimator._get_model_spec(
                    receiver.features, None, tf.estimator.ModeKeys.PREDICT)
                assert not model.sends, "Exported model cannot send"
                assert not model.recvs, "Exported model cannot receive"

                with tf.Session(
                    target=self._cluster_server.target,
                    config=self._cluster_server.cluster_config) as sess:
                    tf.saved_model.simple_save(sess, export_path,
                                               receiver.receiver_tensors,
                                               spec.predictions, None)
                    if self._export_model_hook:
                        self._export_model_hook.after_save(
                            sess, model, export_path,
                            receiver.receiver_tensors, spec.predictions)

    def _request_data_block(self, request):
        """override by subclass"""
        raise RuntimeError("Unimplement")

    def RequestDataBlock(self, request, context):
        if request.worker_rank not in self._running_workers:
            return tm_pb.DataBlockResponse(
                status=common_pb.Status(
                    code=common_pb.StatusCode.STATUS_INVALID_REQUEST,
                    error_message="unregistered worker")
            )

        if request.worker_rank in self._completed_workers:
            return tm_pb.DataBlockResponse(
                status=common_pb.Status(
                    code=common_pb.StatusCode.STATUS_INVALID_REQUEST,
                    error_message="worker has completed")
            )

        return self._request_data_block(request)

    def WorkerRegister(self, request, context):
        with self._lock:
            # for compatibility, more information see:
            #   protocal/fedlearner/common/trainer_master_service.proto
            if self._worker0_cluster_def is None and request.worker_rank == 0:
                self._worker0_cluster_def = request.cluster_def

            if self._status in (tm_pb.MasterStatus.WORKER_COMPLETED,
                                tm_pb.MasterStatus.COMPLETED):
                return tm_pb.WorkerRegisterResponse(
                    status=common_pb.Status(
                        code=common_pb.StatusCode.STATUS_DATA_FINISHED
                    ))

            if self._status != tm_pb.MasterStatus.RUNNING:
                return tm_pb.WorkerRegisterResponse(
                    status=common_pb.Status(
                        code=common_pb.StatusCode. \
                            STATUS_WAIT_FOR_SYNCING_CHECKPOINT
                    ))

            if request.worker_rank in self._running_workers:
                fl_logging.warning("worker_%d:%s repeat registration",
                                   request.worker_rank, request.hostname)
            else:
                fl_logging.info("worker_%d:%s registration",
                                request.worker_rank, request.hostname)

            self._running_workers.add(request.worker_rank)
            if request.worker_rank in self._completed_workers:
                self._completed_workers.remove(request.worker_rank)
            return tm_pb.WorkerRegisterResponse(
                status=common_pb.Status(
                    code=common_pb.StatusCode.STATUS_SUCCESS)
                )

    def WorkerComplete(self, request, context):
        with self._lock:
            if request.worker_rank not in self._running_workers:
                return tm_pb.WorkerRegisterResponse(
                    status=common_pb.Status(
                        code=common_pb.StatusCode.STATUS_INVALID_REQUEST,
                        error_message="unregistered worker")
                    )
            fl_logging.info("worker_%d completed", request.worker_rank)
            self._completed_workers.add(request.worker_rank)
            if request.worker_rank == 0:
                self._worker0_terminated_at = request.timestamp

            if len(self._running_workers) == len(self._completed_workers) \
                and 0 in self._running_workers:
                # worker 0 completed and all datablock has finished
                self._transfer_status(tm_pb.MasterStatus.RUNNING,
                                      tm_pb.MasterStatus.WORKER_COMPLETED)

            return tm_pb.WorkerCompleteResponse(
                status=common_pb.Status(
                    code=common_pb.StatusCode.STATUS_SUCCESS)
                )

    def IsCompleted(self, request, context):
        with self._lock:
            return tm_pb.IsCompletedResponse(
                completed=(self._status == tm_pb.MasterStatus.COMPLETED)
                )


class LeaderTrainerMaster(_TrainerMaster):
    def __init__(self,
                 cluster_server,
                 data_visitor,
                 mode,
                 model_fn,
                 input_fn,
                 serving_input_receiver_fn,
                 checkpoint_filename_with_path=None,
                 checkpoint_path=None,
                 save_checkpoint_steps=None,
                 save_checkpoint_secs=None,
                 summary_path=None,
                 summary_save_steps=None,
                 summary_save_secs=None,
                 export_path=None,
                 sparse_estimator=False,
                 export_model_hook=None):
        super(LeaderTrainerMaster, self).__init__(
            cluster_server,
            "leader",
            mode,
            model_fn,
            input_fn,
            serving_input_receiver_fn,
            checkpoint_filename_with_path,
            checkpoint_path,
            save_checkpoint_steps,
            save_checkpoint_secs,
            summary_path,
            summary_save_steps,
            summary_save_secs,
            export_path,
            sparse_estimator,
            export_model_hook)

        self._data_visitor = data_visitor
        self._last_global_step = -1

        # datavisitor checkpoint hook
        hook = _DataVisitorCheckpointHook(self._data_visitor)
        self._add_checkpoint_listener(
            hook.create_checkpoint_saver_listener())
        self._add_session_hook(hook)

        # trigger hook
        self._last_trigger_time = 0
        self._add_session_hook(
            _TriggerHook(trigger_secs=10,
                         trigger_fn=self._trigger_fn)
            )

    def _trigger_fn(self, global_step):
        now = time.time()
        if self._last_global_step >= 0:
            speed = (global_step-self._last_global_step) \
                / (now-self._last_trigger_time)
            allocated_epoch, allocated_datablock = self._data_visitor.summary()
            total_epoch, total_datablock = \
                self._data_visitor.epoch_num, \
                    self._data_visitor.datablock_size
            fl_logging.info("global_step: %d, speed: %0.2f step/sec, "
                            "epoch: %d/%d, datablock allocated: %d/%d, "
                            "worker: %d/%d(running/completed)",
                            global_step, speed,
                            allocated_epoch, total_epoch,
                            allocated_datablock, total_datablock,
                            len(self._running_workers),
                            len(self._completed_workers))
            with _gctx.stats_client.pipeline() as pipe:
                pipe.gauge("trainer.global_step", global_step)
                pipe.gauge("trainer.datablock_total", total_datablock)
                pipe.gauge("trainer.datablock_allocated", allocated_datablock)
                pipe.gauge("trainer.speed", speed)
        self._last_trigger_time = now
        self._last_global_step = global_step

    def _request_data_block(self, request):
        try:
            data_block = next(self._data_visitor)
        except StopIteration:
            data_block = None

        response = tm_pb.DataBlockResponse()
        if data_block:
            fl_logging.info("allocated worker_%d with block: %s",
                            request.worker_rank,
                            data_block.id)
            response = tm_pb.DataBlockResponse(
                status=common_pb.Status(
                    code=common_pb.StatusCode.STATUS_SUCCESS),
                block_id=data_block.id,
                data_path=data_block.data_path,
            )
        else:
            response = tm_pb.DataBlockResponse(
                status=common_pb.Status(
                    code=common_pb.StatusCode.STATUS_DATA_FINISHED,
                    error_message="data block finished")
                )

        return response


class FollowerTrainerMaster(_TrainerMaster):
    def __init__(self,
                 cluster_server,
                 data_visitor,
                 mode,
                 model_fn,
                 input_fn,
                 serving_input_receiver_fn,
                 checkpoint_filename_with_path=None,
                 checkpoint_path=None,
                 save_checkpoint_steps=None,
                 save_checkpoint_secs=None,
                 summary_path=None,
                 summary_save_steps=None,
                 summary_save_secs=None,
                 export_path=None,
                 sparse_estimator=False,
                 export_model_hook=None):

        super(FollowerTrainerMaster, self).__init__(
            cluster_server,
            "follower",
            mode,
            model_fn,
            input_fn,
            serving_input_receiver_fn,
            checkpoint_filename_with_path,
            checkpoint_path,
            save_checkpoint_steps,
            save_checkpoint_secs,
            summary_path,
            summary_save_steps,
            summary_save_secs,
            export_path,
            sparse_estimator,
            export_model_hook)

        self._data_visitor = data_visitor
        self._last_global_step = -1

        # trigger hook
        self._last_trigger_time = 0
        self._add_session_hook(
            _TriggerHook(trigger_secs=10,
                         trigger_fn=self._trigger_fn)
            )

    def _trigger_fn(self, global_step):
        now = time.time()
        if self._last_global_step >= 0:
            speed = (global_step-self._last_global_step) \
                / (now-self._last_trigger_time)
            total_datablock = self._data_visitor.datablock_size
            fl_logging.info("global_step: %d, speed: %0.2f step/sec, "
                            "datablock size: %d, "
                            "worker: %d/%d(running/completed)",
                            global_step, speed,
                            total_datablock,
                            len(self._running_workers),
                            len(self._completed_workers))
            with _gctx.stats_client.pipeline() as pipe:
                pipe.gauge("trainer.global_step", global_step)
                pipe.gauge("trainer.datablock_total", total_datablock)
                pipe.gauge("trainer.speed", speed)
        self._last_trigger_time = now
        self._last_global_step = global_step

    def _request_data_block(self, request):
        data_block = self._data_visitor.get_datablock_by_id(request.block_id)
        if data_block:
            fl_logging.info("allocated worker_%d with block: %s",
                            request.worker_rank,
                            data_block.id)
            response = tm_pb.DataBlockResponse(
                status=common_pb.Status(
                    code=common_pb.StatusCode.STATUS_SUCCESS),
                block_id=data_block.id,
                data_path=data_block.data_path,
            )
        else:
            fl_logging.error("invalid data block id: %s", request.block_id)
            response = tm_pb.DataBlockResponse(
                status=common_pb.Status(
                    code=common_pb.StatusCode.STATUS_INVALID_DATA_BLOCK,
                    error_message="invalid data block")
                )
        return response

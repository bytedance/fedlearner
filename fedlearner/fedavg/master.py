import os
import time
import threading
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import grpc
import numpy as np

import fedlearner.common.fl_logging as logging
import fedlearner.common.grpc_utils as grpc_utils
from .training_service_pb2 import \
    JoinRequest, JoinResponse, QuitRequest, QuitResponse, \
    PullRequest, PullResponse, PushRequest, PushResponse, Weight, Status
from .training_service_pb2_grpc import TrainingServiceServicer, \
    add_TrainingServiceServicer_to_server, TrainingServiceStub


class _Master:

    def __init__(self, model, steps_per_sync, save_filepath):
        self._model = model

        self._version = 0
        self._timestamp = 0
        self._step = 0
        self._steps_per_sync = steps_per_sync if steps_per_sync > 0 else 1
        self._save_filepath = save_filepath
        self._trainable_weights = \
                {v.name for v in self._model.trainable_weights}

    def on_train_begin(self):
        self._initialize()

    def on_train_batch_begin(self):
        self._step += 1
        return self._step

    def on_train_batch_end(self):
        if self._step % self._steps_per_sync == 0:
            self._sync()

    def on_train_end(self):
        self._save_model()
        self._done()

    def _join(self):
        raise NotImplementedError("_join")

    def _quit(self):
        raise NotImplementedError("_quit")

    def _pull(self, version, is_last_pull=False):
        raise NotImplementedError("_pull")

    def _push(self, step, weights, version, is_train_end):
        raise NotImplementedError("_push")

    def _initialize(self):
        logging.debug("master initialize")
        self._join()

        weight_mapping, version, timestamp = self._pull(self._version)
        self._set_weights(weight_mapping)
        self._version = version
        self._timestamp = timestamp

    def _sync(self):
        logging.debug("master sync")
        weight_mapping = self._get_weights()
        self._version = self._push(self._step, weight_mapping, self._version,
                                   False)
        weight_mapping, version, timestamp = self._pull(self._version)
        assert version == self._version
        self._set_weights(weight_mapping)
        self._timestamp = timestamp

    def _save_model(self):
        logging.debug("master save model")
        weight_mapping = self._get_weights()
        self._version = self._push(self._step, weight_mapping, self._version,
                                   True)
        weight_mapping, version, timestamp = self._pull(self._version, True)
        self._set_weights(weight_mapping)
        self._version = version
        self._timestamp = timestamp

        if self._save_filepath:
            filepath = os.path.join(self._save_filepath, str(self._timestamp))
            self._model.save(filepath)

    def _done(self):
        logging.debug("master quit")
        self._quit()

    def _get_weights(self):
        weight_mapping = {}
        for w, v in zip(self._model.weights, self._model.get_weights()):
            if w.name in self._trainable_weights:
                weight_mapping[w.name] = v
        return weight_mapping

    def _set_weights(self, weight_mapping):
        weights = []
        for w, v in zip(self._model.weights, self._model.get_weights()):
            if w.name in self._trainable_weights \
                and w.name in weight_mapping:
                weights.append(np.reshape(weight_mapping.get(w.name), v.shape))
            else:
                weights.append(v)
        self._model.set_weights(weights)


class _TrainingServiceServicer(TrainingServiceServicer):

    def __init__(self, impl):
        self._impl = impl

    def Join(self, request, context):
        return self._impl._grpc_join_handler(request)  # pylint: disable=protected-access

    def Quit(self, request, context):
        return self._impl._grpc_quit_handler(request)  # pylint: disable=protected-access

    def Pull(self, request, context):
        return self._impl._grpc_pull_handler(request)  # pylint: disable=protected-access

    def Push(self, request, context):
        return self._impl._grpc_push_handler(request)  # pylint: disable=protected-access


class _FollowerSession:

    def __init__(self, name):
        self.name = name
        self.step = 0
        self.join_time = None
        self.quit_time = None
        self.is_train_end = False
        self.latest_version = 0


class LeaderMaster(_Master):

    def __init__(self, model, fl_name, fl_cluster_spec, steps_per_sync,
                 save_filepath):
        super().__init__(model, steps_per_sync, save_filepath)

        self._model = model
        self._fl_name = fl_name
        self._fl_cluster_spec = fl_cluster_spec
        self._leader = self._fl_cluster_spec.leader

        self._follower_mapping = dict()
        for f in self._fl_cluster_spec.followers:
            self._follower_mapping[f.name] = _FollowerSession(f.name)

        self._latest_version = 0
        self._latest_weight_mapping = self._get_weights()
        self._latest_timestamp = int(time.time())
        self._aggregating_version = self._latest_version + 1
        self._aggregating_weight_mapping = dict()
        self._aggregating_weight_count_mapping = dict()
        self._is_quitted = False
        self._lock = threading.RLock()
        self._cv = threading.Condition(self._lock)

    def start(self):
        self._start_grpc_server(self._leader.address)

    def wait(self):
        self._grpc_server.stop(None)

    def _start_grpc_server(self, address):
        self._grpc_server = grpc.server(
            ThreadPoolExecutor(
                max_workers=8,
                thread_name_prefix="LeaderMasterGrpcServerThreadPoolExecutor"))
        add_TrainingServiceServicer_to_server(_TrainingServiceServicer(self),
                                              self._grpc_server)
        self._grpc_server.add_insecure_port(address)
        self._grpc_server.start()
        logging.info('leader master server start on address: %s', address)

    def _follower_join_info(self):
        joined, unjoin = list(), list()
        with self._lock:
            for f in self._follower_mapping.values():
                if f.join_time is not None:
                    joined.append(f.name)
                else:
                    unjoin.append(f.name)
        return joined, unjoin

    def _follower_quit_info(self):
        quitted, unquit = list(), list()
        with self._lock:
            for f in self._follower_mapping.values():
                if f.quit_time is not None:
                    quitted.append(f.name)
                else:
                    unquit.append(f.name)
        return quitted, unquit

    def _follower_push_info(self):
        pushed, unpush, train_end = list(), list(), list()
        with self._lock:
            for f in self._follower_mapping.values():
                if f.is_train_end:
                    train_end.append(f.name)
                elif f.latest_version == self._aggregating_version:
                    pushed.append(f.name)
                else:
                    unpush.append(f.name)
        return pushed, unpush, train_end

    def _join(self):
        with self._lock:
            while True:
                joined, unjoin = self._follower_join_info()
                if not unjoin:
                    logging.info("all followers joined, followers: %s", joined)
                    return

                logging.info(
                    "wait followers join, joined followers: %s,"
                    " unjoin followers: %s", joined, unjoin)
                self._cv.wait(1)

    def _quit(self):
        with self._lock:
            self._is_quitted = True
            while True:
                quitted, unquit = self._follower_quit_info()
                if not unquit:
                    logging.info("all followers quitted, followers: %s",
                                 quitted)
                    return

                logging.info(
                    "wait followers quit, quitted followers: %s,"
                    " unquit followers: %s", quitted, unquit)
                self._cv.wait(1)

    def _pull(self, version, is_last_pull=False):
        return self._latest_weight_mapping, self._latest_version, \
               self._latest_timestamp

    def _push(self, step, weight_mapping, version, is_train_end):
        self._sum_weights(weight_mapping)
        while True:
            with self._lock:
                while True:
                    pushed, unpush, train_end = self._follower_push_info()
                    if not unpush:
                        logging.info(
                            "all followers pushed, version: %d,"
                            " pushed: %s, train_end: %s",
                            self._aggregating_version, pushed, train_end)
                        break

                    logging.info(
                        "wait followers push, pushed follwoers: %s,"
                        " unpushed followers: %s,"
                        " train_end followers: %s", pushed, unpush, train_end)
                    self._cv.wait(1)

            self._aggregate_weights()
            if not is_train_end:
                break

            _, unpush, _ = self._follower_push_info()
            if not unpush:
                break

        return self._latest_version

    def _sum_weights(self, weight_mapping):
        with self._lock:
            for name, weight in weight_mapping.items():
                if name in self._aggregating_weight_mapping:
                    self._aggregating_weight_mapping[name] += weight
                    self._aggregating_weight_count_mapping[name] += 1
                else:
                    self._aggregating_weight_mapping[name] = np.copy(weight)
                    self._aggregating_weight_count_mapping[name] = 1

    def _aggregate_weights(self):
        with self._lock:
            for name in self._aggregating_weight_mapping:
                self._aggregating_weight_mapping[name] /= \
                  self._aggregating_weight_count_mapping[name]

            self._latest_weight_mapping = self._aggregating_weight_mapping
            self._latest_version = self._aggregating_version
            self._latest_timestamp = int(time.time())

            self._aggregating_weight_mapping = dict()
            self._aggregating_weight_count_mapping = dict()
            self._aggregating_version += 1
            logging.info("leader update latest version to %d",
                         self._latest_version)

    def _grpc_join_handler(self, request):
        follower = self._follower_mapping.get(request.name)
        if not follower:
            return JoinResponse(
                Status(code=Status.Code.ERROR,
                       message="invaild follower: {}".format(request.name)))

        with self._lock:
            if not follower.join_time:
                follower.join_time = time.time()
                logging.info("follower: %s join", follower.name)
                self._cv.notify()
            elif follower.quit_time:
                return JoinResponse(status=Status(code=Status.Code.ERROR),
                                    message="quit already")
            else:
                logging.warning("follower: %s join duplicated", follower.name)

        return JoinResponse(status=Status(code=Status.Code.OK))

    def _grpc_quit_handler(self, request):
        follower = self._follower_mapping.get(request.name)
        if not follower:
            return JoinResponse(
                Status(code=Status.Code.ERROR,
                       message="invaild follower: {}".format(request.name)))
        with self._lock:
            if not follower.join_time:
                return QuitResponse(
                    status=Status(code=Status.Code.ERROR, message="not join"))

            if not follower.quit_time:
                follower.quit_time = time.time()
                logging.info("follower: %s quit", follower.name)
                self._cv.notify()
            else:
                logging.warning("follower: %s quit duplicated", follower.name)

        return QuitResponse(status=Status(code=Status.Code.OK))

    def _grpc_pull_handler(self, request):
        follower = self._follower_mapping.get(request.name)
        if not follower:
            return PullResponse(
                Status(code=Status.Code.ERROR,
                       message="invaild follower: {}".format(request.name)))

        with self._lock:
            if not follower.join_time:
                return QuitResponse(
                    status=Status(code=Status.Code.ERROR, message="not join"))
            if follower.quit_time:
                return JoinResponse(status=Status(code=Status.Code.ERROR),
                                    message="quit already")

            if request.is_last_pull:
                if not self._is_quitted:
                    return PullResponse(status=Status(
                        code=Status.Code.NOT_READY))
            elif request.version != self._latest_version:
                return PullResponse(status=Status(code=Status.Code.NOT_READY))

            return PullResponse(status=Status(code=Status.Code.OK),
                                weights=_weight_mapping_to_proto_weights(
                                    self._latest_weight_mapping),
                                version=self._latest_version,
                                timestamp=self._latest_timestamp)

    def _grpc_push_handler(self, request):
        follower = self._follower_mapping.get(request.name)
        if not follower:
            return PullResponse(
                Status(code=Status.Code.ERROR,
                       message="invaild follower: {}".format(request.name)))

        with self._lock:
            if not follower.join_time:
                return PushResponse(
                    status=Status(code=Status.Code.ERROR, message="not join"))
            if follower.quit_time:
                return PushResponse(status=Status(code=Status.Code.ERROR,
                                                  message="quit already"))

            if request.version != follower.latest_version:
                return PushResponse(status=Status(code=Status.Code.ERROR,
                                                  message="invaild version"))

            weight_mapping = dict()
            for w in request.weights:
                weight_mapping[w.name] = _load_ndarray_from_bytes(w.ndarray)

            self._sum_weights(weight_mapping)
            follower.latest_version = self._aggregating_version
            follower.is_train_end = request.is_train_end
            logging.info("follower: %s push version: %s", follower.name,
                         follower.latest_version)
            self._cv.notify_all()

            return PushResponse(status=Status(code=Status.Code.OK),
                                version=self._aggregating_version)


class FollowerMaster(_Master):

    def __init__(self, model, fl_name, fl_cluster_spec, steps_per_sync,
                 save_filepath):
        super().__init__(model, steps_per_sync, save_filepath)

        self._model = model
        self._fl_name = fl_name
        self._fl_cluster_spec = fl_cluster_spec
        self._leader = self._fl_cluster_spec.leader

    def start(self):
        self._grpc_channel = \
            grpc_utils.remote_insecure_channel(self._leader.address)
        self._grpc_client = TrainingServiceStub(self._grpc_channel)

    def wait(self):
        self._grpc_channel.close()

    def _join(self):
        req = JoinRequest(name=self._fl_name)
        resp = grpc_utils.call_with_retry(lambda: self._grpc_client.Join(req))
        if resp.status.code != Status.Code.OK:
            raise RuntimeError(
                "join fed cluster error, code: {}, message: {}".format(
                    resp.status.code, resp.status.message))
        logging.info("join fed cluster success, fl_name: %s", self._fl_name)

    def _quit(self):
        req = QuitRequest(name=self._fl_name)
        resp = grpc_utils.call_with_retry(lambda: self._grpc_client.Quit(req))
        if resp.status.code != Status.Code.OK:
            raise RuntimeError(
                "quit fed cluster error, code: {}, message: {}".format(
                    resp.status.code, resp.status.message))
        logging.info("quit fed cluster success, fl_name: %s", self._fl_name)

    def _pull(self, version, is_last_pull=False):
        req = PullRequest(name=self._fl_name,
                          version=version,
                          is_last_pull=is_last_pull)
        while True:
            resp = grpc_utils.call_with_retry(
                lambda: self._grpc_client.Pull(req))
            if resp.status.code == Status.Code.OK:
                break
            if resp.status.code == Status.Code.NOT_READY:
                logging.info("leader not ready for pull")
                time.sleep(0.2)
            else:
                raise RuntimeError(
                    "pull weights error, code: {}, message: {}".format(
                        resp.status.code, resp.status.message))

        logging.info("pull weights success")
        return _proto_weights_to_weight_mapping(resp.weights), \
            resp.version, resp.timestamp

    def _push(self, step, weight_mapping, version, is_train_end):
        req = PushRequest(
            name=self._fl_name,
            step=step,
            weights=_weight_mapping_to_proto_weights(weight_mapping),
            version=version,
            is_train_end=is_train_end)
        resp = grpc_utils.call_with_retry(lambda: self._grpc_client.Push(req))
        if resp.status.code != Status.Code.OK:
            raise RuntimeError(
                "push weights error, code: {}, message: {}".format(
                    resp.status.code, resp.status.message))

        logging.info("push weights success")
        return resp.version


def _save_ndarray_to_bytes(ndarray):
    b = BytesIO()
    np.save(b, ndarray, allow_pickle=False)
    return b.getvalue()


def _load_ndarray_from_bytes(b):
    return np.load(BytesIO(b), allow_pickle=False)


def _proto_weights_to_weight_mapping(weights):
    weight_mapping = dict()
    for w in weights:
        weight_mapping[w.name] = _load_ndarray_from_bytes(w.ndarray)
    return weight_mapping


def _weight_mapping_to_proto_weights(weight_mapping):
    weights = list()
    for name, ndarray in weight_mapping.items():
        weights.append(
            Weight(name=name, ndarray=_save_ndarray_to_bytes(ndarray)))
    return weights

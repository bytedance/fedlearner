import logging
import queue
import threading
import typing

import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
from fedlearner.data_join.visitors.visitor import Visitor
from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.transmitter.utils import _EndSentinel, \
    ProcessException, PostProcessJob, _queue_iter


class Sender:
    def __init__(self,
                 visitor: Visitor,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 master_client,
                 send_row_num: int,
                 send_queue_len: int = 10,
                 resp_queue_len: int = 10):
        self._visitor = visitor
        self._peer = peer_client
        self._master = master_client
        self._send_row_num = send_row_num
        self._files = []
        self._file_idx = []
        self._started = False
        # whether a task is finished. if True, will try to start a new task
        self._task_finished = True
        self._peer_task_finished = False
        # whether all data is finished.
        self._data_finished = False
        self._stopped = False
        self._send_queue_len = send_queue_len
        self._resp_queue_len = resp_queue_len
        self._send_queue = queue.Queue(send_queue_len)
        self._resp_queue = queue.Queue(resp_queue_len)
        self._condition = threading.Condition()
        self._threads = {}
        self._targets = {'put': self._put,
                         'send': self._send,
                         'resp': self._resp}
        self._routine_worker = RoutineWorker('sender',
                                             self._routine_fn,
                                             self._routine_cond)

    @property
    def finished(self):
        return self._data_finished

    def _stopped_or_finished(self):
        return self._stopped or self._data_finished

    # 1 routine == 1 transmit task
    def _routine_fn(self):
        self._request_task()
        for k, v in self._targets.items():
            assert not (k in self._threads and self._threads[k].is_alive())
            self._threads[k] = threading.Thread(target=v)
            self._threads[k].start()
        self._wait_for_task_finish()
        self._join_threads()

    def _routine_cond(self):
        with self._condition:
            return self._task_finished \
                   and not self._data_finished \
                   and not self._stopped

    def start(self):
        with self._condition:
            assert self._peer and self._master
            if self._stopped:
                raise RuntimeError('[Sender]: Already stopped, cannot restart.')
            if not self._started:
                self._routine_worker.start_routine()

    def _wait_for_task_finish(self):
        if not (self._task_finished
                or self._peer_task_finished
                or self._stopped):
            with self._condition:
                while not (self._task_finished
                           or self._peer_task_finished
                           or self._stopped):
                    self._condition.wait()

    def wait_for_finish(self):
        if not (self._stopped or self._data_finished):
            with self._condition:
                while not (self._stopped or self._data_finished):
                    self._condition.wait()

    def _join_threads(self):
        for t in self._threads.values():
            t.join()

    def stop(self, *args, **kwargs):
        with self._condition:
            if not self._started:
                raise RuntimeError('Sender not yet started.')
            if not self._stopped:
                self._stopped = True
                self._routine_worker.stop_routine()
                self._join_threads()
                self._stop(*args, **kwargs)
                self._condition.notify_all()

    def _request_task(self):
        resp = self._request_task_from_master()
        with self._condition:
            if resp.status == common_pb.STATUS_NO_MORE_DATA:
                self._peer.DataFinish(tsmt_pb.DataFinishRequest())
                self._task_finished = True
                self._data_finished = True
            else:
                self._files = resp.files
                self._file_idx = resp.file_idx
                self._visitor.init(resp.file_info)
                self._task_finished = False
                self._peer_task_finished = False
                self._data_finished = False
            self._condition.notify_all()

    def _put(self):
        if self._data_finished:
            return
        for payload, batch_info in self._send_process():
            if self._stopped:
                return
            self._send_queue.put(tsmt_pb.Request(batch_info=batch_info,
                                                 payload=payload))
        # put a sentinel to tell iterator to stop
        self._send_queue.put(_EndSentinel())

    def _send(self):
        for resp in self._peer.Transmit(_queue_iter(self._send_queue,
                                                    self._stopped_or_finished)):
            if self._stopped:
                break
            if resp.status.code == common_pb.STATUS_INVALID_REQUEST:
                # TODO(zhangzihui): error handling
                logging.warning('[Sender]: INVALID REQUEST responded: %s', resp)
                continue
            self._resp_queue.put(resp)
        self._resp_queue.put(_EndSentinel())

    def _resp(self):
        for resp in _queue_iter(self._resp_queue, self._stopped_or_finished):
            self._resp_process(resp)
        with self._condition:
            self._task_finished = True
            self._condition.notify_all()

    def _request_task_from_master(self):
        raise NotImplementedError

    def report_peer_file_finish_to_master(self, file_idx: int):
        raise NotImplementedError

    def set_peer_task_finished(self):
        with self._condition:
            self._peer_task_finished = True
            self._condition.notify_all()

    def _stop(self, *args, **kwargs):
        """
        Called before stopping, for shutting down custom objects like dumper.
            No need to overwrite if nothing needs to be done at exit.
        Returns:

        """
        pass

    def _send_process(self) -> typing.Iterable[bytes, tsmt_pb.BatchInfo]:
        """
        This method handles file processing payload. This should iterate the
            visitor and process the content it returns.

        Returns:
            a payload bytes,
            a BatchInfo describing this batch.
        """
        raise NotImplementedError('_send_process not implemented.')

    def _resp_process(self,
                      resp: tsmt_pb.Response) -> None:
        """
        This method handles the response returned by server. Return True if
            nothing is needed to do.
        Args:
            resp: a tsmt_pb.Response to handle.

        NOTE: Channel will return response in the original order of send
            sequence, but peer might start from a former index(after restart),
            so it is possible to have duplicate response.

        Returns:
            an IDX indicating where the state on disk should be updated to.
                Return None if no need to save a new state. Note that this IDX
                may be staler than meta's, meaning that some part of this resp
                is fully processed and the remaining part is still processing.
        """
        raise NotImplementedError('_resp_process not implemented.')


class Receiver:
    def __init__(self,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 output_path: str,
                 recv_queue_len: int):
        self._peer = peer_client
        self._output_path = output_path
        self._recv_queue_len = recv_queue_len
        self._recv_queue = queue.Queue(recv_queue_len)
        self._recv_thread = threading.Thread(target=self._recv)
        self._batch_idx = 0
        self._condition = threading.Condition()
        self._started = False
        self._data_finished = False
        self._stopped = False

    @property
    def finished(self):
        return self._data_finished

    def _stopped_or_finished(self):
        return self._stopped or self._data_finished

    # RPC
    def transmit(self, request_iterator: typing.Iterable):
        # one ongoing transmit at the same time
        with self._condition:
            for r in request_iterator:
                if self._stopped:
                    break
                if self._data_finished:
                    raise RuntimeError('The stream has already finished.')

                # Channel assures us there is a subsequence of requests that
                #   constitutes the original req sequence, including order,
                #   so we need to check if it is consecutive.
                consecutive = self._batch_idx == r.batch_idx
                try:
                    payload, post_job = self._recv_process(r, consecutive)
                except ProcessException as e:
                    yield tsmt_pb.Response(
                        status=common_pb.Status(
                            code=common_pb.STATUS_INVALID_REQUEST,
                            error_message=repr(e)))
                # status is good from here as bad status has been returned
                else:
                    status = common_pb.Status()
                    status.MergeFrom(r.status)
                    yield tsmt_pb.Response(status=status,
                                           file_idx=r.file_idx,
                                           batch_idx=r.batch_idx,
                                           payload=payload)

                if consecutive:
                    self._recv_queue.put((r.batch_info, post_job))
                    self._batch_idx += 1

            self._recv_queue.put(_EndSentinel())

    # RPC
    def data_finish(self):
        with self._condition:
            self._data_finished = True
            self._condition.notify_all()
        return tsmt_pb.DataFinishResponse()

    def start(self):
        if self._stopped:
            raise RuntimeError('[Receiver]: Already stopped, cannot restart.')
        if self._started:
            return
        with self._condition:
            self._started = True
            self._recv_thread.start()

    def wait_for_finish(self):
        if not (self._stopped or self._data_finished):
            with self._condition:
                while not (self._stopped or self._data_finished):
                    self._condition.wait()

    def stop(self, *args, **kwargs):
        with self._condition:
            if not self._stopped:
                self._stop(*args, **kwargs)
                self._stopped = True
                self._condition.notify_all()

    def _recv(self):
        while not self._data_finished and not self._stopped:
            for batch_info, job in _queue_iter(self._recv_queue,
                                               self._stopped_or_finished):
                if job:
                    job.run()
                if batch_info.finished:
                    self._peer.RecvFileFinish(tsmt_pb.RecvFileFinishRequest(
                        file_idx=batch_info.file_idx))
            self._peer.RecvTaskFinish(tsmt_pb.RecvTaskFinishRequest())

    def _stop(self, *args, **kwargs):
        """
        Called before stopping, for shutting down custom objects like dumper.
            No need to inherit if nothing needs to be done at exit.
        Returns:

        """
        pass

    def _recv_process(self,
                      req: tsmt_pb.Request,
                      consecutive: bool) -> (bytes, [PostProcessJob, None]):
        """
        This method should handle preceded and duplicated requests properly,
            and NOTE THAT SENDER MAY SEND DUPLICATED REQUESTS EVEN WHEN THE
            RECEIVER IS FINISHED, as the sender might not receive the response.

        Args:
            req: a request pb
            consecutive: whether this request is the next expected request

        Returns:
            a payload bytes string. Return None if no payload to respond.
            a PostTask object that will be run later. Return None if no post
                task needs to be run later.
        """
        raise NotImplementedError('_receive_process not implemented.')

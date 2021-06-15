import logging
import queue
import threading
import typing

import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.transmitter.utils import _EndSentinel, \
    ProcessException, PostTask


class Sender:
    def __init__(self,
                 send_row_num: int,
                 send_queue_len: int = 10,
                 resp_queue_len: int = 10):
        self._transmitter = None
        self._send_row_num = send_row_num
        self._files = []
        self._file_idx = []
        self._started = False
        # whether a task is finished. if True, will try to start a new task
        self._task_finished = True
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
        with self._condition:
            return self._data_finished

    def add_transmitter(self, transmitter):
        with self._condition:
            self._transmitter = transmitter

    # 1 routine == 1 transmit task
    def _routine_fn(self):
        self._task_finished = False
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
            assert self._transmitter
            if self._stopped:
                raise RuntimeError('[Sender]: Already stopped, cannot restart.')
            if not self._started:
                self._routine_worker.start_routine()

    def _wait_for_task_finish(self):
        if not self._task_finished and not self._stopped:
            with self._condition:
                while not self._task_finished and not self._stopped:
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

    def _queue_iter(self, q: queue.Queue):
        while not self._stopped:
            # use timeout to check condition rather than blocking continuously.
            # Queue object is thread-safe, no need to use Lock.
            try:
                req = q.get(timeout=5)
                if isinstance(req, _EndSentinel):
                    break
                yield req
            except queue.Empty:
                pass

    def _request_task(self):
        assert self._transmitter
        resp = self._transmitter.allocate_task()
        with self._condition:
            if resp.status == common_pb.STATUS_NO_MORE_DATA:
                self._transmitter.data_finish_c(tsmt_pb.DataFinishRequest())
                self._task_finished = True
                self._data_finished = True
            else:
                self._files = resp.files
                self._file_idx = resp.file_idx
                self._transmitter.sync_c(
                    tsmt_pb.SyncRequest(file_idx=self._file_idx[0]))
                self._task_finished = False
                self._data_finished = False
            self._condition.notify_all()

    def _put(self):
        for file, file_idx, next_idx in zip(self._files,
                                            self._file_idx,
                                            self._file_idx[1:] + [-1]):
            batch_idx = 0
            while True:
                if self._stopped:
                    return

                with self._condition:
                    payload, file_finished = self._send_process(
                        file, self._send_row_num, self._send_queue_len)
                if file_finished:
                    status = common_pb.Status(
                        code=common_pb.STATUS_FILE_FINISHED)
                    self._send_queue.put(tsmt_pb.Request(status=status,
                                                         file_idx=file_idx,
                                                         next_idx=next_idx,
                                                         batch_idx=batch_idx,
                                                         payload=payload))
                    break
                # else file not yet finished
                batch_idx += 1
                # queue.put will block if no slot available
                status = common_pb.Status(code=common_pb.STATUS_SUCCESS)
                self._send_queue.put(tsmt_pb.Request(status=status,
                                                     file_idx=file_idx,
                                                     next_idx=next_idx,
                                                     batch_idx=batch_idx,
                                                     payload=payload))
        # put a sentinel to tell iterator to stop
        self._send_queue.put(_EndSentinel())

    def _send(self):
        for resp in self._transmitter.transmit_c(
            self._queue_iter(self._send_queue)
        ):
            if self._stopped:
                break
            if resp.status.code == common_pb.STATUS_INVALID_REQUEST:
                # TODO(zhangzihui): error handling
                logging.warning('[Sender]: INVALID REQUEST responded: %s', resp)
                continue
            self._resp_queue.put(resp)
        self._resp_queue.put(_EndSentinel())

    def _resp(self):
        for resp in self._queue_iter(self._resp_queue):
            self._resp_process(resp)
            if resp.status.code == common_pb.STATUS_FILE_FINISHED:
                self._transmitter.report_finish(resp.file_idx, 'send')
        with self._condition:
            self._task_finished = True
            self._condition.notify_all()

    def _stop(self, *args, **kwargs):
        """
        Called before stopping, for shutting down custom objects like dumper.
            No need to inherit if nothing needs to be done at exit.
        Returns:

        """
        pass

    def _send_process(self,
                      file_path: str,
                      row_num: int,
                      send_queue_len: int) -> (bytes, bool):
        """
        This method handles file reading and returns the payload.
        Args:
            file_path: path to the file to read.
            row_num: suggested num of lines to read.
            send_queue_len: len of buffer queue.

        Returns:
            a payload bytes,
            a bool indicating whether the file is finished.
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
                 output_path: str,
                 recv_queue_len: int):
        self._transmitter = None
        self._output_path = output_path
        self._recv_queue_len = recv_queue_len
        self._recv_queue = queue.Queue(recv_queue_len)
        self._recv_thread = threading.Thread(target=self._recv)
        self._file_idx = -1
        self._batch_idx = 0
        self._condition = threading.Condition()
        self._started = False
        self._synced = False
        self._data_finished = False
        self._stopped = False

    def add_transmitter(self, transmitter):
        assert not (self._stopped or self._started)
        with self._condition:
            self._transmitter = transmitter

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

    def _queue_iter(self, q: queue.Queue):
        while not self._stopped:
            # use timeout to check condition rather than blocking continuously.
            # Queue object is thread-safe, no need to use Lock.
            try:
                req = q.get(timeout=5)
                if isinstance(req, _EndSentinel):
                    break
                yield req
            except queue.Empty:
                pass

    # RPC
    def sync(self, request: tsmt_pb.SyncRequest):
        with self._condition:
            self._file_idx = request.file_idx
            self._data_finished = False
            self._synced = True
        return tsmt_pb.SyncResponse()

    # RPC
    def transmit(self, request_iterator: typing.Iterable):
        for r in request_iterator:
            if self._stopped:
                break
            if self._data_finished:
                raise RuntimeError('The stream has already finished.')

            # whether this request is the expected next request
            consecutive = self._check_req_consecutive(r)
            with self._condition:
                # Channel assures us there is a subsequence of requests that
                #   constitutes the original requests sequence, including order,
                #   so we need to deal with preceded and duplicated requests.
                try:
                    payload, task = self._recv_process(r, consecutive)
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
                    self._recv_queue.put((r.status, r.file_idx, task))
                    # if file finished, reset indices
                    if r.status.code == common_pb.STATUS_FILE_FINISHED:
                        self._file_idx = r.next_idx
                        self._batch_idx = 0
                    else:
                        self._batch_idx += 1
        self._recv_queue.put(_EndSentinel())

    # RPC
    def data_finish(self):
        with self._condition:
            self._data_finished = True
        return tsmt_pb.DataFinishResponse()

    def _recv(self):
        for status, file_idx, task in self._queue_iter(self._recv_queue):
            if task:
                task.run()
            if status.code == common_pb.STATUS_FILE_FINISHED:
                self._transmitter.recv_file_finish_c(
                    tsmt_pb.RecvFileFinishRequest(file_idx=file_idx))
        with self._condition:
            self._recv_process_finished = True

    def _check_req_consecutive(self, req: tsmt_pb.Request):
        return self._file_idx == req.file_idx \
               and self._batch_idx == req.batch_idx

    def _stop(self, *args, **kwargs):
        """
        Called before stopping, for shutting down custom objects like dumper.
            No need to inherit if nothing needs to be done at exit.
        Returns:

        """
        pass

    def _recv_process(self,
                      req: tsmt_pb.Request,
                      consecutive: bool) -> (bytes, [PostTask, None]):
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

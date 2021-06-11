import logging
import queue
import threading
import typing

import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.transmitter.utils import _EndSentinel, \
    RecvProcessException


class Sender:
    def __init__(self,
                 rank_id: int,
                 send_row_num: int,
                 pending_len: int = 10):
        self._rank_id = rank_id
        self._send_row_num = send_row_num
        self._files = []
        self._file_idx = []
        self._client = None
        self._master_client = None
        self._started = False
        # whether a task is finished. if True, will try to start a new task
        self._task_finished = True
        # whether all data is finished.
        self._data_finished = False
        self._stopped = False
        self._request_queue = queue.Queue(pending_len)
        self._condition = threading.Condition()
        self._put_thread = None
        self._send_thread = None
        self._routine_worker = RoutineWorker('sender',
                                             self._routine_fn,
                                             self._routine_cond)

    @property
    def finished(self):
        with self._condition:
            return self._data_finished

    def add_peer_client(self, client: tsmt_grpc.TransmitterWorkerServiceStub):
        with self._condition:
            if not self._client:
                self._client = client

    def add_master_client(self,
                          client: tsmt_grpc.TransmitterMasterServiceStub):
        with self._condition:
            if not self._master_client:
                self._master_client = client

    def _request_task(self):
        assert self._master_client
        resp = self._master_client.AllocateTask(
            tsmt_pb.AllocateTaskRequest(rank_id=self._rank_id))
        with self._condition:
            if resp.status == common_pb.STATUS_NO_MORE_DATA:
                self._client.Finish(tsmt_pb.DataFinishRequest())
                self._data_finished = True
            else:
                self._files = resp.files
                self._file_idx = resp.file_idx
                self._task_finished = False
            self._condition.notify_all()

    def _put_requests(self):
        for file, file_idx in zip(self._files, self._file_idx):
            batch_idx = 0
            while True:
                if self._stopped:
                    return

                with self._condition:
                    payload, file_finished = self._send_process(
                        file, self._send_row_num)
                if file_finished:
                    status = common_pb.Status(
                        code=common_pb.STATUS_FILE_FINISHED)
                    self._request_queue.put(tsmt_pb.Request(status=status,
                                                            file_idx=file_idx,
                                                            batch_idx=batch_idx,
                                                            payload=payload))
                    break
                # else file not yet finished
                batch_idx += 1
                # queue.put will block if no slot available
                status = common_pb.Status(code=common_pb.STATUS_SUCCESS)
                self._request_queue.put(tsmt_pb.Request(status=status,
                                                        file_idx=file_idx,
                                                        batch_idx=batch_idx,
                                                        payload=payload))
        # put a sentinel to tell iterator to stop
        self._request_queue.put(_EndSentinel())

    def _requests_iterator(self):
        while not (self._stopped or self._data_finished or self._task_finished):
            # use timeout to check condition rather than blocking continuously.
            # Queue object is thread-safe, no need to use Lock.
            try:
                req = self._request_queue.get(timeout=5)
                if isinstance(req, _EndSentinel):
                    break
                yield req
            except queue.Empty:
                pass

    def _send(self):
        for resp in self._client.Transmit(self._requests_iterator()):
            if self._stopped:
                break
            if resp.status.code == common_pb.STATUS_INVALID_REQUEST:
                # TODO(zhangzihui): error handling
                logging.warning('[Sender]: INVALID REQUEST responded: %s', resp)
                continue
            file_finish = resp.status.code == common_pb.STATUS_FILE_FINISHED
            with self._condition:
                self._resp_process(resp)
            if file_finish:
                fin_resp = self._master_client.FinishFiles(
                    tsmt_pb.FinishFilesRequest(rank_id=self._rank_id,
                                               file_idx=[resp.file_idx]))
                if fin_resp.status == common_pb.STATUS_NOT_PROCESSING:
                    logging.warning('[Sender]: {}'.format(fin_resp.err_msg))
        else:
            with self._condition:
                self._task_finished = True
                self._condition.notify_all()

    def _wait_for_task_finish(self):
        if not self._task_finished and not self._stopped:
            with self._condition:
                while not self._task_finished and not self._stopped:
                    self._condition.wait()

    def _routine_fn(self):
        self._task_finished = False
        self._request_task()
        self._put_thread = threading.Thread(target=self._put_requests)
        self._send_thread = threading.Thread(target=self._send)
        self._put_thread.start()
        self._send_thread.start()
        self._wait_for_task_finish()

    def _routine_cond(self):
        with self._condition:
            return self._task_finished \
                   and not self._data_finished \
                   and not self._stopped

    def start(self):
        with self._condition:
            assert self._client and self._master_client
            if self._stopped:
                raise RuntimeError('Sender has been stopped.')
            if not self._started:
                self._routine_worker.start_routine()

    def wait_for_finish(self):
        if not (self._stopped or self._data_finished):
            with self._condition:
                while not (self._stopped or self._data_finished):
                    self._condition.wait()

    def stop(self, *args, **kwargs):
        with self._condition:
            if not self._started:
                raise RuntimeError('Sender not yet started.')
            if not self._stopped:
                self._stopped = True
                self._routine_worker.stop_routine()
                self._put_thread.join()
                self._send_thread.join()
                self._stop(*args, **kwargs)
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
                      row_num: int) -> (bytes, bool):
        """
        This method handles file reading and returns the payload.
        Args:
            row_num: suggested num of lines to read.

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
                 output_path: str):
        self._output_path = output_path
        self._file_idx = -1
        self._batch_idx = 0
        self._condition = threading.Condition()
        self._started = False
        self._task_finished = False
        self._data_finished = False
        self._stopped = False

    @property
    def finished(self) -> bool:
        with self._condition:
            return self._task_finished

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

    def data_finish(self):
        with self._condition:
            self._data_finished = True
        return tsmt_pb.DataFinishResponse()

    def transmit(self, request_iterator: typing.Iterable):
        for r in request_iterator:
            if self._stopped:
                break
            if self._task_finished:
                raise RuntimeError('The stream has already finished.')
            with self._condition:
                # Channel assures us there is a subsequence of requests that
                #   constitutes the original requests sequence, including order,
                #   so we need to deal with preceded and duplicated requests.
                yield self._process_request(r)
                # if file finished, reset indices
                if r.status.code == common_pb.STATUS_FILE_FINISHED:
                    self._file_idx = -1
                    self._batch_idx = 0
                else:
                    self._batch_idx += 1
        else:
            # only finish when all requests have been processed, as sender may
            #   miss some responses and send some duplicates
            with self._condition:
                self._task_finished = True
                self._file_idx = -1
                self._batch_idx = 0

    def _process_request(self, req: tsmt_pb.Request):
        with self._condition:
            try:
                payload = self._recv_process(
                    req, self._file_idx, self._batch_idx)
            except RecvProcessException as e:
                return tsmt_pb.Response(
                    status=common_pb.Status(
                        code=common_pb.STATUS_INVALID_REQUEST,
                        error_message=repr(e)))
            # status is good from here as bad status has been returned
            status = common_pb.Status()
            status.MergeFrom(req.status)
            return tsmt_pb.Response(status=status,
                                    file_idx=req.file_idx,
                                    batch_idx=req.batch_idx,
                                    payload=payload)

    def _stop(self, *args, **kwargs):
        """
        Called before stopping, for shutting down custom objects like dumper.
            No need to inherit if nothing needs to be done at exit.
        Returns:

        """
        pass

    def _recv_process(self,
                      req: tsmt_pb.Request,
                      file_idx: int,
                      batch_idx: int) -> [bytes, None]:
        """
        This method should handle preceded and duplicated requests properly,
            and NOTE THAT SENDER MAY SEND DUPLICATED REQUESTS EVEN WHEN THE
            RECEIVER IS FINISHED, as the sender might not receive the response.

        Args:
            req: a request pb
            file_idx: an int indicating the current transmit file.
            batch_idx: an int indicating the expected receive batch.

        Returns:
            a payload bytes string.
            an IDX indicating where the meta should be updated to and saved.
                Return None if no need to save state.

        NOTE:
            after transmit finishes, meta will be automatically saved regardless
                of the IDX returned here.
        """
        raise NotImplementedError('_receive_process not implemented.')

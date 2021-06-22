import logging
import queue
import threading
import typing

from google.protobuf import empty_pb2
import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
from fedlearner.data_join.transmitter.utils import _EndSentinel, _queue_iter


class Sender(object):
    def __init__(self,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 send_queue_len: int = 10,
                 resp_queue_len: int = 10):
        self._peer = peer_client
        # whether a task is finished. if True, will try to start a new task
        self._local_task_finished = threading.Event()
        self._peer_task_finished = threading.Event()
        # whether sender is finished.
        self._finished = threading.Event()
        self._send_queue_len = send_queue_len
        self._resp_queue_len = resp_queue_len
        self._send_queue = queue.Queue(send_queue_len)
        self._resp_queue = queue.Queue(resp_queue_len)
        self._targets = [self._put, self._send, self._resp]
        self._thread = None

    @property
    def finished(self):
        return self._finished.isSet()

    def start(self):
        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def wait_for_finished(self):
        if not self._thread:
            raise RuntimeError("Sender not started yet")
        while not self._finished.isSet():
            logging.info("Waiting sender to finish...")
            self._finished.wait()

    def _run(self):
        while True:
            resp = self._request_task_from_master()
            if resp.status == common_pb.STATUS_NO_MORE_DATA:
                self._peer.DataFinish(empty_pb2.Empty())
                break
            self._local_task_finished.clear()
            self._peer_task_finished.clear()
            for target_fn in self._targets:
                thread = threading.Thread(target=target_fn)
                thread.start()
            self._wait_for_task_finish()
        self._finished.set()

    def _wait_for_task_finish(self):
        while not self._local_task_finished.isSet():
            logging.info("Waiting local task finished")
            self._local_task_finished.wait()
        while not self._peer_task_finished.isSet():
            logging.info("Waiting peer task finished")
            self._peer_task_finished.wait()

    def _put(self):
        for payload, batch_info in self._data_iterator():
            self._send_queue.put(tsmt_pb.TransmitDataRequest(
                batch_info=batch_info, payload=payload))
        # put a sentinel to tell iterator to stop
        self._send_queue.put(_EndSentinel())

    def _send(self):
        for resp in self._peer.TransmitData(_queue_iter(self._send_queue)):
            if resp.status.code == common_pb.STATUS_INVALID_REQUEST:
                # TODO(zhangzihui): error handling
                logging.warning('[Sender]: INVALID REQUEST responded: %s', resp)
                continue
            self._resp_queue.put(resp)
        self._resp_queue.put(_EndSentinel())

    def _resp(self):
        for resp in _queue_iter(self._resp_queue):
            self._resp_process(resp)
        self._local_task_finished.set()

    def _request_task_from_master(self):
        raise NotImplementedError

    def report_peer_file_finish_to_master(self, file_idx: int) \
            -> common_pb.Status:
        raise NotImplementedError

    def set_peer_task_finished(self):
        self._peer_task_finished.set()

    def _data_iterator(self) -> typing.Iterable[bytes, tsmt_pb.BatchInfo]:
        """
        This method handles file processing payload. This should iterate the
            visitor and process the content it returns.

        Returns:
            a payload bytes,
            a BatchInfo describing this batch.
        """
        raise NotImplementedError('_send_process not implemented.')

    def _resp_process(self,
                      resp: tsmt_pb.TransmitDataResponse) -> None:
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


class Receiver(object):
    def __init__(self,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 recv_queue_len: int = 10):
        self._peer = peer_client
        self._recv_queue_len = recv_queue_len
        self._recv_queue = queue.Queue(recv_queue_len)
        self._thread = None
        self._finished = threading.Event()
        self._lock = threading.Lock()
        self._batch_idx = 0

    @property
    def finished(self):
        return self._finished.isSet()

    def start(self):
        self._thread = threading.Thread(target=self._recv)
        self._thread.start()

    def wait_for_finish(self):
        if not self._thread:
            raise RuntimeError("Sender not started yet")
        while not self._finished.isSet():
            logging.info("Waiting sender to finish...")
            self._finished.wait()

    # RPC
    def transmit(self, request_iterator: typing.Iterable):
        # one ongoing transmit at the same time
        for r in request_iterator:
            if self._finished.isSet():
                raise RuntimeError('The stream has already finished.')

            # Channel assures us there is a subsequence of requests that
            #   constitutes the original req sequence, including order,
            #   so we need to check if it is consecutive.
            with self._lock:
                consecutive = self._batch_idx == r.batch_idx
                payload, post_job = self._recv_process(r, consecutive)
                if consecutive:
                    self._recv_queue.put((r.batch_info, post_job))
                    self._batch_idx += 1
            status = common_pb.Status()
            status.MergeFrom(r.status)
            yield tsmt_pb.TransmitDataResponse(status=status,
                                               file_idx=r.file_idx,
                                               batch_idx=r.batch_idx,
                                               payload=payload)
        self._recv_queue.put(_EndSentinel())

    # RPC
    def data_finish(self):
        self._finished.set()
        return common_pb.Status(code=common_pb.StatusCode.STATUS_SUCCESS)

    def _recv(self):
        while not self._finished.isSet():
            for batch_info, job in _queue_iter(self._recv_queue):
                if job:
                    job()
                if batch_info.finished:
                    self._peer.RecvFileFinish(tsmt_pb.RecvFileFinishRequest(
                        file_idx=batch_info.file_idx))
            self._peer.RecvTaskFinish(empty_pb2.Empty())

    def _recv_process(self,
                      req: tsmt_pb.TransmitDataRequest,
                      consecutive: bool) -> (bytes, [object, None]):
        """
        This method should handle preceded and duplicated requests properly,
            and NOTE THAT SENDER MAY SEND DUPLICATED REQUESTS EVEN WHEN THE
            RECEIVER IS FINISHED, as the sender might not receive the response.

        Args:
            req: a request pb
            consecutive: whether this request is the next expected request

        Returns:
            a payload bytes string. Return None if no payload to respond.
            a post task object that will be run later. Return None if no post
                task needs to be run later.
        """
        raise NotImplementedError('_receive_process not implemented.')

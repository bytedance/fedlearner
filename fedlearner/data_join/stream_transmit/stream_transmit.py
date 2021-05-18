import json
import logging
import os
import queue
import threading
import typing

from tensorflow import gfile
from tensorflow.python.lib.io import file_io

import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.stream_transmit_pb2 as st_pb
import fedlearner.common.stream_transmit_pb2_grpc as st_grpc
from fedlearner.channel.channel import Channel


def _encode_meta_path(meta_dir, mode):
    assert mode in ('send', 'recv')
    return os.path.join(meta_dir, '{}.meta'.format(mode))


def _check_order(r: [st_pb.Request, st_pb.Response], file_index, row_index):
    preceded = r.file_index > file_index \
               or (r.file_index == file_index
                   and r.row_index > row_index)
    duplicated = r.file_index < file_index \
                 or (r.file_index == file_index
                     and r.row_index < row_index)
    return preceded, duplicated


class RecvProcessException(Exception):
    pass


class Sender:
    def __init__(self,
                 meta_dir: str,
                 send_row_num: int,
                 file_paths: typing.List[str],
                 root_path: str = None,
                 pending_len: int = 10):
        self._meta_path = _encode_meta_path(meta_dir, 'send')
        self._send_row_num = send_row_num
        self._client = None
        # The meta is used in ACK.
        self._meta = self._get_meta(file_paths, root_path or '')
        self._synced = False
        self._started = False
        self._finished = self._meta['finished']
        self._stopped = False
        self._request_queue = queue.Queue(pending_len)
        self._condition = threading.Condition()
        self._put_thread = threading.Thread(target=self._put_requests)
        self._send_thread = threading.Thread(target=self._send)

    @property
    def finished(self):
        with self._condition:
            return self._finished

    def _get_meta(self,
                  file_paths: list,
                  root_path: str):
        if gfile.Exists(self._meta_path):
            with gfile.GFile(self._meta_path) as mf:
                meta = json.load(mf)
        else:
            meta = {
                'file_index': 0,
                'row_index': 0,
                'root': root_path,
                'files': file_paths,
                'finished': False
            }
            file_io.atomic_write_string_to_file(self._meta_path,
                                                json.dumps(meta))
        return meta

    def add_client(self, client: st_grpc.StreamTransmitServiceStub):
        with self._condition:
            if not self._client:
                self._client = client

    def _sync(self):
        resp = self._client.SyncState(st_pb.SyncRequest())
        with self._condition:
            if self._meta['file_index'] > resp.file_index:
                self._send_file_idx = resp.file_index
                self._send_row_idx = resp.row_index
                self._finished = False
            elif self._meta['file_index'] == resp.file_index and \
                    self._meta['row_index'] > resp.row_index:
                self._send_file_idx = self._meta['file_index']
                self._send_row_idx = resp.row_index
                self._finished = False
            # else sender has staler state, so use the sender's state
            else:
                self._send_file_idx = self._meta['file_index']
                self._send_row_idx = resp.row_index
            self._synced = True

    def _send(self):
        if not self._synced:
            raise RuntimeError('Sender not yet synced with peer.')
        for resp in self._client.Transmit(self._request_iterator()):
            if self._stopped:
                break
            with self._condition:
                # Channel will return response in the original order, without
                # any duplicates, so no need to check preceded & duplicated
                forward = self._resp_process(resp)
                if resp.status.code == common_pb.STATUS_INVALID_REQUEST:
                    # TODO(zhangzihui): error handling
                    logging.warning(
                        '[Transmit]: STATUS_INVALID_REQUEST returned: %s', resp)
                    continue
                elif resp.status.code == common_pb.STATUS_SUCCESS:
                    self._meta['file_index'] = resp.file_index
                    self._meta['row_index'] = resp.row_index
                elif resp.status.code == common_pb.STATUS_FILE_FINISHED:
                    self._meta['file_index'] = resp.file_index + 1
                    self._meta['row_index'] = 0
                elif resp.status.code == common_pb.STATUS_DATA_FINISHED:
                    self._meta['file_index'] = resp.file_index + 1
                    self._meta['row_index'] = 0
                    self._meta['finished'] = True
                    self._finished = True
                    self._condition.notify_all()

                if forward:
                    file_io.atomic_write_string_to_file(self._meta_path,
                                                        json.dumps(self._meta))

    def start(self):
        with self._condition:
            assert self._client
            if not self._started:
                self._sync()
                self._put_thread.start()
                self._send_thread.start()
                self._started = True

    def wait_for_finish(self):
        if not self.finished:
            with self._condition:
                while not self.finished:
                    self._condition.wait()

    def stop(self):
        with self._condition:
            if not self._stopped:
                self._stopped = True
                self._put_thread.join()
                self._send_thread.join()
                self._condition.notify_all()

    def _put_requests(self):
        assert self._synced
        root_path = self._meta['root']
        to_be_sent = self._meta['file'][self._send_file_idx:]
        for index, file in enumerate(to_be_sent):
            if self._stopped:
                break
            file_finished = False
            while not file_finished and not self._stopped:
                payload, row_num, file_finished = self._send_process(
                    os.path.join(root_path, file),
                    row_index=self._send_row_idx,
                    row_num=self._send_row_num
                )

                if file_finished:
                    if len(to_be_sent) == index - 1:
                        status = common_pb.Status(
                            code=common_pb.STATUS_DATA_FINISHED)
                    else:
                        status = common_pb.Status(
                            code=common_pb.STATUS_FILE_FINISHED)
                else:
                    status = common_pb.Status(code=common_pb.STATUS_SUCCESS)
                req = st_pb.Request(status=status,
                                    file_index=self._send_file_idx + index,
                                    row_index=self._send_row_idx,
                                    row_num=row_num,
                                    payload=payload)
                self._send_row_idx += row_num
                # Queue will block this thread if no slot available.
                self._request_queue.put(req)
            self._send_row_idx = 0

    def _request_iterator(self):
        while not self._finished and not self._stopped:
            # use timeout to check condition rather than blocking continuously.
            # Queue object is thread-safe, no need to use Lock.
            try:
                yield self._request_queue.get(timeout=5)
            except queue.Empty:
                pass

    def _send_process(self,
                      file_path: str,
                      row_index: int,
                      row_num: int) -> (bytes, int, bool):
        """
        This method handles file reading and build a base request. The request
            it returns should fill `payload` and `row_num` field.
        Args:
            file_path: the file to read.
            row_index: from which line to read.
            row_num: suggested num of lines to read. `row_num` field in the
                returned request can be different to this arg.

        Returns:
            a payload bytes,
            a int indicating how many rows are read,
            a bool indicating whether this file finishes.
        """
        raise NotImplementedError('_send_process not implemented.')

    def _resp_process(self,
                      resp: st_pb.Response) -> bool:
        """
        This method handles the response returned by server. Return True if
            nothing is needed to do.
        Args:
            resp: a st_pb.Response to handle.

        NOTE: Channel will return response in the original order of send
            sequence, so no need for preceded & duplicated checks.

        Returns:
            whether to save the state. Return True if nothing is needed to do.
        """
        raise NotImplementedError('_resp_process not implemented.')


class Receiver:
    def __init__(self,
                 meta_dir: str,
                 output_path: str):
        self._meta_path = _encode_meta_path(meta_dir, 'recv')
        self._meta = self._get_meta(output_path)
        self._output_path = self._meta['output_path']
        self._finished = self._meta['finished']
        self._condition = threading.Condition()
        self._stopped = False

    @property
    def finished(self):
        with self._condition:
            return self._finished

    def _get_meta(self, output_path: str):
        if gfile.Exists(self._meta_path):
            with gfile.GFile(self._meta_path) as mf:
                meta = json.load(mf)
        else:
            meta = {
                'output_path': output_path,
                'file_index': 0,
                'row_index': 0,
                'finished': False
            }
            file_io.atomic_write_string_to_file(self._meta_path,
                                                json.dumps(meta))
        return meta

    def wait_for_finish(self):
        if not self.finished:
            with self._condition:
                while not self.finished:
                    self._condition.wait()

    def stop(self):
        if self.finished:
            with self._condition:
                self._stopped = True
                self._condition.notify_all()

    def sync_state(self):
        with self._condition:
            return st_pb.SyncResponse(file_index=self._meta['file_index'],
                                      row_index=self._meta['row_index'])

    def transmit(self, request_iterator: typing.Iterable):
        for r in request_iterator:
            if self._stopped:
                break
            if self.finished:
                raise RuntimeError('The stream has already finished.')
            with self._condition:
                # Channel assures us there is a subsequence of requests that
                #   constitutes the original requests sequence, including order,
                #   so we need to deal with preceded and duplicated requests.
                preceded, duplicated = _check_order(r,
                                                    self._meta['file_index'],
                                                    self._meta['row_index'])
                yield self._process_request(r, preceded, duplicated)
        else:
            with self._condition:
                self._meta['finished'] = True
                self._finished = True

    def _process_request(self,
                         req: st_pb.Request,
                         preceded: bool,
                         duplicated: bool):
        with self._condition:
            try:
                payload, forward = self._process(
                    req,
                    preceded=preceded,
                    duplicated=duplicated
                )
            except RecvProcessException as e:
                return st_pb.Response(status=common_pb.Status(
                    code=common_pb.STATUS_INVALID_REQUEST,
                    error_message=repr(e)
                ))

            if req.status.code == common_pb.STATUS_FILE_FINISHED:
                self._meta['file_index'] = req.file_index + 1
                self._meta['row_index'] = 0
                status = common_pb.Status(code=common_pb.STATUS_FILE_FINISHED)
            elif req.status.code == common_pb.STATUS_DATA_FINISHED:
                self._meta['file_index'] = req.file_index + 1
                self._meta['row_index'] = 0
                # should not finish as there may be some duplicates to process.
                status = common_pb.Status(code=common_pb.STATUS_DATA_FINISHED)
            else:
                self._meta['row_index'] = req.row_index + req.row_num
                status = common_pb.Status(code=common_pb.STATUS_SUCCESS)

            if forward:
                file_io.atomic_write_string_to_file(self._meta_path,
                                                    json.dumps(self._meta))

            return st_pb.Response(status=status,
                                  file_index=req.file_index,
                                  row_index=req.row_index,
                                  row_num=req.row_num,
                                  payload=payload)

    def _process(self,
                 req: st_pb.Request,
                 preceded: bool,
                 duplicated: bool) -> (bytes, bool):
        """
        This method should handle preceded and duplicated requests properly,
            and NOTE THAT SENDER MAY SEND DUPLICATED REQUESTS EVEN WHEN THE
            RECEIVER IS FINISHED, as the sender might not receive the response.

        Args:
            req: a request pb
            preceded: whether this request is behind the expected next request.
                i.e., a latter request arrive before a former request.
            duplicated: whether this request is duplicated.

        Returns:
            A payload bytes string, and a bool indicating whether the meta
                should be dumped(saved). The bool should be True when a file or
                a dumper finishes and the state needs to be recorded.
        """
        raise NotImplementedError('_receive_process not implemented.')


class _StreamTransmitServicer(st_grpc.StreamTransmitServiceServicer):
    def __init__(self,
                 receiver: Receiver):
        self._receiver = receiver

    def SyncState(self, request, context):
        self._receiver.sync_state()

    def Transmit(self, request_iterator, context):
        self._receiver.transmit(request_iterator)


class StreamTransmit:
    def __init__(self,
                 listen_port: [str, int],
                 remote_address: str,
                 receiver: Receiver,
                 sender: Sender = None):
        """
        Class for transmitting data with fail-safe.
        Args:
            listen_port: port to listen gRPC request.
            remote_address: remote StreamTransmit address.
            receiver: Receiver object to handle received requests and Channel
                requests. This is needed even when it is only a client.
            sender: Sender object to send requests.
        """

        self._receiver = receiver
        self._listen_address = "[::]:{}".format(listen_port)
        self._remote_address = remote_address
        self._server = Channel(self._listen_address, self._remote_address)
        self._server.subscribe(self._channel_callback)
        st_grpc.add_StreamTransmitServiceServicer_to_server(
            _StreamTransmitServicer(self._receiver),
            self._server)
        if sender:
            self._sender = sender
            self._client = st_grpc.StreamTransmitServiceStub(self._server)
            self._sender.add_client(self._client)
        else:
            self._client = None
            self._sender = None
        self._condition = threading.Condition()
        self._connected = False
        self._terminated = False

    def _channel_callback(self, channel, event):
        if event == Channel.Event.PEER_CLOSED:
            self._receiver.stop()
            if self._sender:
                self._sender.stop()
        if event == Channel.Event.ERROR:
            err = channel.error()
            logging.fatal('[Bridge] suicide as channel exception: %s, '
                          'maybe caused by peer restart', repr(err))
            exit(138)  # Tell Scheduler to restart myself

    def connect(self):
        with self._condition:
            if self._connected:
                return
            self._connected = True
            self._server.connect()
            if self._sender:
                self._sender.start()

    def wait_for_finish(self):
        self._receiver.wait_for_finish()
        if self._sender:
            self._sender.wait_for_finish()

    def terminate(self):
        with self._condition:
            if not self._connected:
                return
            if self._terminated:
                return
            self._terminated = True
            self._condition.notify_all()
            self._receiver.stop()
            if self._sender:
                self._sender.stop()
            self._server.close()

import logging
import threading
import typing

import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
from fedlearner.channel.channel import Channel
from fedlearner.data_join.transmitter.components import Sender, Receiver
from fedlearner.proxy.channel import make_insecure_channel, ChannelType


class TransmitterWorker:
    class Servicer(tsmt_grpc.TransmitterWorkerServiceServicer):
        def __init__(self, transmitter):
            self._transmitter = transmitter

        # from RECV to SEND
        def RecvFileFinish(self, request, context):
            return self._transmitter.recv_file_finish(request)

        # from SEND to RECV
        def Sync(self, request, context):
            return self._transmitter.sync(request)

        def Transmit(self, request_iterator, context):
            return self._transmitter.transmit(request_iterator)

        def DataFinish(self, request, context):
            return self._transmitter.data_finish()

    def __init__(self,
                 rank_id: int,
                 listen_port: [str, int],
                 master_address: str,
                 remote_address: str,
                 sender: Sender,
                 receiver: Receiver):
        """
        Class for transmitting data with fail-safe.
        Args:
            listen_port: port to listen gRPC request.
            remote_address: remote StreamTransmit address.
        """
        self._rank_id = rank_id
        self._listen_address = "[::]:{}".format(listen_port)
        self._remote_address = remote_address
        self._sender = sender
        self._receiver = receiver
        self._sender.add_transmitter(self)
        self._receiver.add_transmitter(self)

        self._finish_record = {'send': set(), 'recv': set(), 'finish': set()}

        self._server = Channel(self._listen_address, self._remote_address)
        self._server.subscribe(self._channel_callback)
        tsmt_grpc.add_TransmitterWorkerServiceServicer_to_server(
            TransmitterWorker.Servicer(self), self._server)
        self._peer = tsmt_grpc.TransmitterWorkerServiceStub(self._server)

        master_channel = make_insecure_channel(
            master_address, ChannelType.INTERNAL,
            options=[('grpc.max_send_message_length', 2 ** 31 - 1),
                     ('grpc.max_receive_message_length', 2 ** 31 - 1)]
        )
        self._master = tsmt_grpc.TransmitterMasterServiceStub(master_channel)
        self._condition = threading.Condition()

        self._started = False
        self._stopped = False

    def start(self):
        with self._condition:
            if self._stopped:
                raise RuntimeError('[Transmitter]: Already stopped.')
            if self._started:
                return
            self._started = True
            self._sender.start()
            self._receiver.start()
            self._server.connect()

    def wait_for_finish(self):
        self._sender.wait_for_finish()
        self._receiver.wait_for_finish()

    def stop(self):
        with self._condition:
            if not self._started:
                return
            if self._stopped:
                return
            self._stopped = True
            self._condition.notify_all()
            self._server.close()
            self._sender.stop()
            self._receiver.stop()

    def _channel_callback(self, channel, event):
        if event == Channel.Event.PEER_CLOSED:
            self.stop()
        if event == Channel.Event.ERROR:
            err = channel.error()
            logging.fatal('[Bridge] suicide as channel exception: %s, '
                          'maybe caused by peer restart', repr(err))
            exit(138)  # Tell Scheduler to restart myself

    # RPCs
    # ======== as a WORKER ======== #
    def allocate_task(self, request: tsmt_pb.AllocateTaskRequest):
        return self._master.AllocateTask(request)

    def report_finish(self, file_idx: int, kind: str):
        assert kind in ('send', 'recv')
        if file_idx in self._finish_record['finish']:
            return
        opposite = 'recv' if kind == 'send' else 'send'
        if file_idx in self._finish_record[opposite]:
            self._master.FinishFiles(tsmt_pb.FinishFilesRequest(
                rank_id=self._rank_id,
                file_idx=[file_idx]))
            self._finish_record[opposite].discard(file_idx)
            self._finish_record['finish'].add(file_idx)
        else:
            self._finish_record[kind].add(file_idx)

    # ======== as a CLIENT ======== #
    # `c` == `client`
    def sync_c(self, request: tsmt_pb.SyncRequest):
        return self._peer.Sync(request)

    def transmit_c(self, request_iterator: typing.Iterable):
        return self._peer.Transmit(request_iterator)

    def data_finish_c(self, request: tsmt_pb.DataFinishRequest):
        return self._peer.DataFinish(request)

    def recv_file_finish_c(self, request: tsmt_pb.RecvFileFinishRequest):
        return self._peer.RecvFileFinish(request)

    # ======== as a SERVER ======== #
    def sync(self, request: tsmt_pb.SyncRequest):
        return self._receiver.sync(request)

    def transmit(self, request_iterator: typing.Iterable):
        return self._receiver.transmit(request_iterator)

    def data_finish(self):
        return self._receiver.data_finish()

    def recv_file_finish(self, request: tsmt_pb.RecvFileFinishRequest):
        self.report_finish(request.file_idx, 'recv')
        return tsmt_pb.RecvFileFinishResponse()

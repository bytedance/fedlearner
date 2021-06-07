import logging
import threading

import fedlearner.common.transmitter_service_pb2_grpc as transmitter_grpc
from fedlearner.channel.channel import Channel
from fedlearner.data_join.transmitter.components import Sender, Receiver


class _StreamTransmitServicer(transmitter_grpc.TransmitterServiceServicer):
    def __init__(self,
                 receiver: Receiver):
        self._receiver = receiver

    def SyncState(self, request, context):
        return self._receiver.sync_state(request)

    def Transmit(self, request_iterator, context):
        return self._receiver.transmit(request_iterator)


class Transmitter:
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
        transmitter_grpc.add_TransmitterServiceServicer_to_server(
            _StreamTransmitServicer(self._receiver),
            self._server)
        if sender:
            self._sender = sender
            self._client = transmitter_grpc.TransmitterServiceStub(self._server)
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

import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
from fedlearner.data_join.transmitter.components import Sender, Receiver


class TransmitterWorkerServicer(tsmt_grpc.TransmitterWorkerServiceServicer):
    def __init__(self,
                 receiver: Receiver,
                 sender: Sender):
        self._receiver = receiver
        self._sender = sender

    # from RECV to SEND
    def RecvFileFinish(self, request, context):
        return self._sender.report_peer_file_finish_to_master(
            request.file_idx)

    def RecvTaskFinish(self, request, context):
        self._sender.set_peer_task_finished()
        return tsmt_pb.RecvTaskFinishResponse()

    # from SEND to RECV
    def Sync(self, request, context):
        return self._receiver.sync(request)

    def Transmit(self, request_iterator, context):
        return self._receiver.transmit(request_iterator)

    def DataFinish(self, request, context):
        return self._receiver.data_finish()

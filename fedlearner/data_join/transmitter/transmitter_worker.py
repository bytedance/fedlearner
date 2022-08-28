import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
from fedlearner.common import common_pb2 as common_pb
from fedlearner.data_join.transmitter.components import Sender, Receiver


class TransmitterWorker(tsmt_grpc.TransmitterWorkerServiceServicer):
    def __init__(self,
                 receiver: Receiver,
                 sender: Sender):
        self._receiver = receiver
        self._sender = sender

    # from RECV to SEND
    def RecvFileFinish(self, request, context):
        if not self._sender:
            raise NotImplementedError('Method not implemented!')
        return self._sender.report_peer_file_finish_to_master(
            request.file_idx)

    def RecvTaskFinish(self, request, context):
        if not self._sender:
            raise NotImplementedError('Method not implemented!')
        self._sender.set_peer_task_finished()
        return common_pb.Status(code=common_pb.StatusCode.STATUS_SUCCESS)

    # from SEND to RECV
    def TransmitData(self, request_iterator, context):
        if not self._receiver:
            raise NotImplementedError('Method not implemented!')
        return self._receiver.transmit(request_iterator)

    def DataFinish(self, request, context):
        if not self._receiver:
            raise NotImplementedError('Method not implemented!')
        return self._receiver.data_finish()

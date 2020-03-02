import sys
import logging
from fedlearner.common import scheduler_service_pb2 as ss_pb
from fedlearner.common import scheduler_service_pb2_grpc as ss_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType


class SchedulerServer(ss_grpc.SchedulerServicer):
    def __init__(self, receiver_fn):
        super(SchedulerServer, self).__init__()
        self._receiver_fn = receiver_fn

    def SubmitJob(self, request, context):
        response = ss_pb.Status
        try:
            response = self._receiver_fn(request)
        except Exception:  # pylint: disable=broad-except
            response.state_code = ss_pb.JobStateCode.INTERNAL_ERROR
            response.error_message = sys.exc_info()[0]
        return response


class SchedulerClient(object):
    def __init__(self, addr):
        self._addr = addr
        channel = make_insecure_channel(addr, mode=ChannelType.REMOTE)
        self._stub = ss_grpc.SchedulerStub(channel)

    def submit_train(self, request):
        result = self._stub.SubmitTrainJob(request)
        if result.state_code == ss_pb.JobStateCode.SUCCESS:
            logging.debug("%s:%d submit success.", result.application_id,
                          result.error_code)
            return True
        logging.error("%s:%d submit failed with error[%s].",
                      result.application_id, result.error_code,
                      result.error_message)
        return False

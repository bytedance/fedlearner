# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

import sys
import logging
from fedlearner.common import scheduler_service_pb2_grpc as ss_grpc
from fedlearner.common import common_pb2 as common_pb
from fedlearner.proxy.channel import make_insecure_channel, ChannelType


class SchedulerServer(ss_grpc.SchedulerServicer):
    def __init__(self, receiver_fn):
        super(SchedulerServer, self).__init__()
        self._receiver_fn = receiver_fn

    def SubmitTrainJob(self, request, context):
        response = common_pb.Status()
        try:
            response = self._receiver_fn(request)
        except Exception:  # pylint: disable=broad-except
            response.ode = common_pb.StatusCode.STATUS_UNKNOWN_ERROR
            response.error_message = sys.exc_info()[0]
        return response


class SchedulerClient(object):
    def __init__(self, addr):
        self._addr = addr
        channel = make_insecure_channel(addr, mode=ChannelType.REMOTE)
        self._stub = ss_grpc.SchedulerStub(channel)

    def submit_train(self, request):
        result = self._stub.SubmitTrainJob(request)
        if result.code == common_pb.StatusCode.STATUS_SUCCESS:
            logging.info("code [%d] submit success.", result.code)
            return True
        logging.error("code [%d] submit failed with error[%s].", result.code,
                      result.error_message)
        return False

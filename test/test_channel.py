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

import unittest
from fedlearner_common.proxy.channel import *
from fedlearner_common.protobuf import trainer_master_service_pb2 as tm_pb
from fedlearner_common.protobuf import trainer_master_service_pb2_grpc as tm_grpc


class TestChannel(unittest.TestCase):
    def test_channel(self):
        channel = make_insecure_channel('worker_0', mode=ChannelType.INTERNAL)
        stub = tm_grpc.TrainerMasterServiceStub(channel)
        request = tm_pb.DataBlockRequest()
        print(stub.RequestDataBlock(request))
        self.assertIsNotNone(stub.RequestDataBlock(request))

        channel = make_insecure_channel('worker_0', mode=ChannelType.REMOTE)
        stub = tm_grpc.TrainerMasterServiceStub(channel)
        request = tm_pb.DataBlockRequest()
        print(stub.RequestDataBlock(request))
        self.assertIsNotNone(stub.RequestDataBlock(request))


if __name__ == '__main__':
    unittest.main()

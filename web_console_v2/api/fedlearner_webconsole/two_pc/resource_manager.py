# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
from abc import abstractmethod
from typing import Tuple

from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData, TwoPcAction


class ResourceManager(object):
    """An abstract class to manage resource in 2pc.

    The recommendation practice is to keep those methods idempotent.
    """

    def __init__(self, tid: str, data: TransactionData):
        self.tid = tid
        self.data = data

    @abstractmethod
    def prepare(self) -> Tuple[bool, str]:
        pass

    @abstractmethod
    def commit(self) -> Tuple[bool, str]:
        pass

    @abstractmethod
    def abort(self) -> Tuple[bool, str]:
        pass

    def run_two_pc(self, action: TwoPcAction) -> Tuple[bool, str]:
        if action == TwoPcAction.PREPARE:
            return self.prepare()
        if action == TwoPcAction.COMMIT:
            return self.commit()
        assert action == TwoPcAction.ABORT
        return self.abort()

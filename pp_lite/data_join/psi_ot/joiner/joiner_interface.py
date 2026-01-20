# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import List
from abc import ABCMeta, abstractmethod
from pp_lite.proto.common_pb2 import DataJoinType


class Joiner(metaclass=ABCMeta):

    def __init__(self, joiner_port: int):
        self.joiner_port = joiner_port

    @property
    @abstractmethod
    def type(self) -> DataJoinType:
        raise NotImplementedError

    @abstractmethod
    def client_run(self, ids: List[str]) -> List[str]:
        """Run data join at client side. The id's in intersection set is returned"""
        raise NotImplementedError

    @abstractmethod
    def server_run(self, ids: List[str]) -> List[str]:
        """Run data join at server side. The id's in intersection set is returned"""
        raise NotImplementedError

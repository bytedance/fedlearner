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

from abc import abstractmethod, ABCMeta
from typing import Optional

from fedlearner_webconsole.proto.serving_pb2 import RemoteDeployConfig, RemoteDeployState


class IRemoteServing(metaclass=ABCMeta):
    """Deploy model on remote third-party serving platform

    """

    @abstractmethod
    def deploy_model(self, creator: str, config: RemoteDeployConfig) -> Optional[int]:
        pass

    @abstractmethod
    def get_deploy_url(self, config: RemoteDeployConfig) -> str:
        pass

    @abstractmethod
    def validate_config(self, config: RemoteDeployConfig) -> bool:
        pass

    @abstractmethod
    def get_deploy_status(self, config: RemoteDeployConfig) -> RemoteDeployState:
        return RemoteDeployState.REMOTE_DEPLOY_READY

    @abstractmethod
    def undeploy_model(self, config: RemoteDeployConfig):
        pass


supported_remote_serving = {}


def register_remote_serving(name: str, serving: IRemoteServing):
    supported_remote_serving[name] = serving

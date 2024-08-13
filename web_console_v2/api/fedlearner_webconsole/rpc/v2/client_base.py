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

from abc import ABC
from typing import Optional

import grpc
from envs import Envs

from fedlearner_webconsole.rpc.v2.auth_client_interceptor import AuthClientInterceptor
from fedlearner_webconsole.utils.decorators.lru_cache import lru_cache


@lru_cache(timeout=60, maxsize=100)
def build_grpc_channel(nginx_controller_url: str,
                       peer_domain_name: str,
                       project_name: Optional[str] = None) -> grpc.Channel:
    """A helper function to build gRPC channel with cache.

    Notice that as we cache the channel, if nginx controller gets restarted, the channel may break.
    This practice is following official best practice: https://grpc.io/docs/guides/performance/

    Args:
        nginx_controller_url: Nginx controller url in current cluster,
            e.g. fedlearner-stack-ingress-nginx-controller.default.svc:80
        peer_domain_name: Domain name of the peer which we want to connect to, e.g. fl-test.com
        project_name: Project name which the client works on.

    Returns:
        A grpc service channel to construct grpc clients.
    """
    # Authority is used to route the traffic out of cluster, specificly it will look like fl-test-client-auth.com
    domain_name_prefix = peer_domain_name.rpartition('.')[0]
    authority = f'{domain_name_prefix}-client-auth.com'

    channel = grpc.insecure_channel(
        target=nginx_controller_url,
        # options defined at
        # https://github.com/grpc/grpc/blob/master/include/grpc/impl/codegen/grpc_types.h
        options=[('grpc.default_authority', authority)])

    x_host = f'fedlearner-webconsole-v2.{peer_domain_name}'
    # Adds auth client interceptor to auto-populate auth related headers
    channel = grpc.intercept_channel(channel, AuthClientInterceptor(x_host=x_host, project_name=project_name))
    return channel


def get_nginx_controller_url() -> str:
    """Generates nginx controller url in current cluster.

    Basically our gRPC client talks to the nginx controller.
    """
    if Envs.DEBUG and Envs.GRPC_SERVER_URL is not None:
        return Envs.GRPC_SERVER_URL
    return 'fedlearner-stack-ingress-nginx-controller.default.svc:80'


class ParticipantRpcClient(ABC):
    """Abstract class for clients which only work on participant system level, e.g. system service to check health.
    """

    def __init__(self, channel: grpc.Channel):
        pass

    @classmethod
    def from_participant(cls, domain_name: str):
        channel = build_grpc_channel(
            get_nginx_controller_url(),
            domain_name,
        )
        return cls(channel)


class ParticipantProjectRpcClient(ABC):
    """Abstract class for clients which work on participant's project level, e.g. model service to train/eval.
    """

    def __init__(self, channel: grpc.Channel):
        pass

    @classmethod
    def from_project_and_participant(cls, domain_name: str, project_name: str):
        channel = build_grpc_channel(
            get_nginx_controller_url(),
            domain_name,
            project_name,
        )
        return cls(channel)

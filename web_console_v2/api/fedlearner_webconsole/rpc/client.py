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
# pylint: disable=broad-except

import logging
import grpc
from fedlearner_webconsole.proto import (
    service_pb2, service_pb2_grpc, common_pb2
)


def _build_channel(url, authority):
    """A helper function to build gRPC channel for easy testing."""
    return grpc.insecure_channel(
            target=url,
            # options defined at
            # https://github.com/grpc/grpc/blob/master/include/grpc/impl/codegen/grpc_types.h
            # options={
            #     'grpc.default_authority': authority,
            # }
    )


class RpcClient(object):
    def __init__(self, project_config, receiver_config):
        self._project = project_config
        self._receiver = receiver_config
        self._auth_info = service_pb2.ProjAuthInfo(
            project_name=self._project.name,
            source_domain=self._project.domain_name,
            target_domain=self._receiver.domain_name,
            auth_token=self._project.token)

        self._client = service_pb2_grpc.WebConsoleV2ServiceStub(_build_channel(
            self._receiver.grpc_spec.peer_url,
            self._receiver.grpc_spec.authority
        ))

    def _get_metadata(self):
        metadata = []
        for key, value in self._receiver.grpc_spec.extra_headers.items():
            metadata.append((key, value))
        # metadata is a tuple of tuples
        return tuple(metadata)

    def check_connection(self):
        msg = service_pb2.CheckConnectionRequest(
            auth_info=self._auth_info)
        try:
            response = self._client.CheckConnection(
                request=msg, metadata=self._get_metadata())
            if response.status.code != common_pb2.STATUS_SUCCESS:
                logging.debug('check_connection request error: %s',
                              response.status.msg)
            return response.status
        except Exception as e:
            logging.debug('check_connection request error: %s', repr(e))
            return common_pb2.Status(
                code=common_pb2.STATUS_UNKNOWN_ERROR,
                msg=repr(e))

    def update_workflow_state(self, name, state, target_state,
                              transaction_state):
        msg = service_pb2.UpdateWorkflowStateRequest(
            auth_info=self._auth_info,
            workflow_name=name,
            state=state.value,
            target_state=target_state.value,
            transaction_state=transaction_state.value)
        try:
            response = self._client.UpdateWorkflowState(
                request=msg, metadata=self._get_metadata())
            if response.status.code != common_pb2.STATUS_SUCCESS:
                logging.debug(
                    'update_workflow_state request error: %s',
                    response.status.msg)
            return response
        except Exception as e:
            logging.debug('update_workflow_state request error: %s', repr(e))
            return service_pb2.UpdateWorkflowStateResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR,
                    msg=repr(e)))

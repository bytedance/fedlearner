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

import os
import grpc
from fedlearner_webconsole.proto import (
    service_pb2, service_pb2_grpc, common_pb2
)
from fedlearner_webconsole.project.models import Project


def _build_channel(url, authority):
    """A helper function to build gRPC channel for easy testing."""
    return grpc.insecure_channel(
            target=url,
            # options defined at
            # https://github.com/grpc/grpc/blob/master/include/grpc/impl/codegen/grpc_types.h
            options={
                'grpc.default_authority': authority,
            }
    )


class RpcClient(object):
    def __init__(self, project_id, receiver_name):
        project = Project.query.filter_by(
            name=project_id).first()
        assert project is not None, \
            'project {} not found'.format(project_id)
        self._project = project.get_config()
        self._project.project_name = project.name
        self._receiver = next((participant for participant in self._project.participants
                               if participant.name == receiver_name), None)
        assert self._receiver is not None, \
            'receiver {} not found'.format(receiver_name)

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
            auth_info=service_pb2.ProjAuthInfo(
                project_name=self._project.project_name,
                sender_name=os.environ.get('SELF_DOMAIN_NAME'),
                receiver_name=self._receiver.domain_name,
                auth_token=self._project.token))
        try:
            response = self._client.CheckConnection(
                request=msg, metadata=self._get_metadata())
            return response.status
        except Exception as e:
            return common_pb2.Status(
                code=common_pb2.STATUS_UNKNOWN_ERROR,
                msg=repr(e))

    def update_workflow(self, uuid, status, name,
                              forkable, config,
                              peer_config, method_type):
        msg = service_pb2.UpdateWorkflowRequest(
            auth_info=service_pb2.ProjAuthInfo(
                project_name=self._project.project_name,
                sender_name=os.environ.get('SELF_DOMAIN_NAME'),
                receiver_name=self._receiver.domain_name,
                auth_token=self._project.token),
            uuid=uuid, status=status, name=name, forkable=forkable,
            config=config, peer_config=peer_config,
            method_type=method_type
        )
        try:
            response = self._client.UpdateWorkflow(
                request=msg, metadata=self._get_metadata())
            return response.status
        except Exception as e:
            return common_pb2.Status(
                code=common_pb2.STATUS_UNKNOWN_ERROR,
                msg=repr(e))

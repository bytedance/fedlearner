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

import grpc
from fedlearner_webconsole.proto import (
    service_pb2, service_pb2_grpc, common_pb2
)
from fedlearner_webconsole.project.models import Project


class RPCClient(object):
    def __init__(self, project_name, receiver_name):
        project = Project.query.filter_by(
            name=project_name).first()
        assert project is not None, \
            'project %s not found' % project_name
        self._project = project.get_config()
        assert receiver_name in self._project.participants, \
            'receiver %s not found' % receiver_name
        self._receiver = self._project.participants[receiver_name]

        channel = grpc.insecure_channel(self._receiver.url)
        self._client = service_pb2_grpc.WebConsoleV2ServiceStub(channel)

    def check_connection(self):
        msg = service_pb2.CheckConnectionRequest(
            auth_info=service_pb2.ProjAuthInfo(
                project_name=self._project.project_name,
                sender_name=self._project.self_name,
                receiver_name=self._receiver.name,
                auth_token=self._receiver.sender_auth_token))
        try:
            return self._client.CheckConnection(msg).status
        except Exception as e:
            return common_pb2.Status(
                code=common_pb2.STATUS_UNKNOWN_ERROR,
                msg=repr(e))

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
import logging
from grpc import RpcError

from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.exceptions import InvalidArgumentException
class WorkflowGrpc:
    def _grpc_update_workflow(self, uuid, status, project_name,
                              method_type, name=None,
                              forkable=None, config=None,
                              peer_config=None):
        """
        CREATE_SENDER_PREPARE = 1
        CREATE_RECEIVER_PREPARE = 2
        CREATE_SENDER_COMMITTABLE = 3
        CREATE_RECEIVER_COMMITTABLE  = 4
        CREATED = 5
        FORK_SENDER = 6
        config should be binary-byte string.
        """
        # TODO: implement multi-participants
        project = Project.query.filter_by(name=project_name).first()
        if project is None:
            raise InvalidArgumentException('RPC: project does not exist')
        receiver_names = project.get_config().participants.keys()
        for receiver_name in receiver_names:
            stub = RpcClient(project_name=project_name,
                             receiver_name=receiver_name)
            result = stub.update_workflow(uuid, status, name,
                                          forkable, config,
                                          peer_config, method_type)
            if result.code == common_pb2.STATUS_UNKNOWN_ERROR:
                logging.error('RPC: to %s %s, failed msg: %s', project_name,
                              receiver_name, result.msg)
                raise RpcError
            if result.code == common_pb2.STATUS_UNAUTHORIZED:
                logging.error('RPC: %s %s Unauthorized.', project_name
                              , receiver_name)
                raise RpcError
            logging.warning('RPC: %s %s %s peer succeeded update. msg:%s',
                         project_name,
                         receiver_name, name, result.msg)

    def create_workflow(self, uuid, name, config, project_name, forkable):
        # TODO: implement 2pc (TCC) try() confirm() cancel()
        return self._grpc_update_workflow(uuid=uuid, project_name=project_name,
                                          name=name, status=2,
                                          forkable=forkable, peer_config=config,
                                          method_type=common_pb2.CREATE)

    def confirm_workflow(self, uuid, config, project_name, forkable):
        # TODO: implement 2pc (TCC) try() confirm() cancel()
        return self._grpc_update_workflow(uuid=uuid, project_name=project_name,
                                          status=5,
                                          forkable=forkable, peer_config=config,
                                          method_type=common_pb2.UPDATE)

    def fork_workflow(self, uuid, name, project_name, config, peer_config):
        # TODO: implement 2pc (TCC) try() confirm() cancel()
        return self._grpc_update_workflow(uuid=uuid, name=name,
                                          project_name=project_name, status=5,
                                          config=peer_config,
                                          peer_config=config,
                                          method_type=common_pb2.FORK)

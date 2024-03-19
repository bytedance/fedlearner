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
import logging
from typing import List, Tuple
from uuid import uuid4

from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.proto.two_pc_pb2 import TwoPcAction, TwoPcType, TransactionData
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.two_pc.handlers import run_two_pc_action
from fedlearner_webconsole.utils.metrics import emit_store


class TransactionManager(object):

    def __init__(self, project_name: str, project_token: str, participants: List[str], two_pc_type: TwoPcType):
        self.type = two_pc_type
        self._project_name = project_name
        self._project_token = project_token
        self._clients = []
        for domain_name in participants:
            self._clients.append(
                RpcClient.from_project_and_participant(project_name=self._project_name,
                                                       project_token=self._project_token,
                                                       domain_name=domain_name))

    def run(self, data: TransactionData) -> Tuple[bool, str]:
        tid = str(uuid4())
        prepared, pre_message = self.do_two_pc_action(tid, TwoPcAction.PREPARE, data)
        # TODO(hangweiqiang): catch exception and maybe retry sometime?
        if prepared:
            succeeded, act_message = self.do_two_pc_action(tid, TwoPcAction.COMMIT, data)
        else:
            succeeded, act_message = self.do_two_pc_action(tid, TwoPcAction.ABORT, data)
        if not succeeded:
            emit_store('2pc.transaction_failure', 1)
        return (prepared, pre_message) if not prepared else (succeeded, act_message)

    def do_two_pc_action(self, tid: str, action: TwoPcAction, data: TransactionData) -> Tuple[bool, str]:
        # TODO(hangweiqiang): using multi-thread
        succeeded = True
        message = None
        for client in self._clients:
            result, res_message = self._remote_do_two_pc(client, tid, action, data)
            if not result and succeeded:
                succeeded = False
                message = res_message
        result, res_message = self._local_do_two_pc(tid, action, data)
        if not result and succeeded:
            succeeded = False
            message = res_message
        return succeeded, message

    def _remote_do_two_pc(self, client: RpcClient, tid: str, action: TwoPcAction,
                          data: TransactionData) -> Tuple[bool, str]:
        response = client.run_two_pc(transaction_uuid=tid, two_pc_type=self.type, action=action, data=data)
        if response.status.code != common_pb2.STATUS_SUCCESS:
            # Something wrong during rpc call
            logging.info('[%s] 2pc [%s] error [%s]: %s', self.type, action, tid, response.status.msg)
            return False, response.message
        if not response.succeeded:
            # Failed
            logging.info('[%s] 2pc [%s] failed [%s]: %s', self.type, action, tid, response.message)
            return False, response.message
        return True, response.message

    def _local_do_two_pc(self, tid: str, action: TwoPcAction, data: TransactionData) -> Tuple[bool, str]:
        try:
            with db.session_scope() as session:
                succeeded, message = run_two_pc_action(session=session,
                                                       tid=tid,
                                                       two_pc_type=self.type,
                                                       action=action,
                                                       data=data)
                session.commit()
        except Exception as e:  # pylint: disable=broad-except
            succeeded = False
            message = str(e)
        if not succeeded:
            logging.info('[%s] 2pc [%s] failed locally [%s]: %s', self.type, action, tid, message)
        return succeeded, message

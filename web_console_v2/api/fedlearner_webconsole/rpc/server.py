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
# pylint: disable=broad-except, cyclic-import

import threading
from concurrent import futures
import grpc
from fedlearner_webconsole.proto import (
    service_pb2, service_pb2_grpc, common_pb2
)
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.workflow.models import (
    Workflow, WorkflowState, TransactionState
)
from fedlearner_webconsole.scheduler.transaction import TransactionManager

from fedlearner_webconsole.exceptions import (
    UnauthorizedException
)

class RPCServerServicer(service_pb2_grpc.WebConsoleV2ServiceServicer):
    def __init__(self, server):
        self._server = server

    def CheckConnection(self, request, context):
        try:
            return self._server.check_connection(request)
        except UnauthorizedException as e:
            return service_pb2.CheckConnectionResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNAUTHORIZED,
                    msg=repr(e)))
        except Exception as e:
            return service_pb2.CheckConnectionResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR,
                    msg=repr(e)))

    def UpdateWorkflowState(self, request, context):
        try:
            return self._server.update_workflow_state(request)
        except UnauthorizedException as e:
            return service_pb2.UpdateWorkflowStateResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNAUTHORIZED,
                    msg=repr(e)))
        except Exception as e:
            return service_pb2.UpdateWorkflowStateResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR,
                    msg=repr(e)))


class RpcServer(object):

    def __init__(self):
        self._lock = threading.Lock()
        self._started = False
        self._server = None

    def start(self, listen_port):
        assert not self._started, "Already started"
        with self._lock:
            self._server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=10))
            service_pb2_grpc.add_WebConsoleV2ServiceServicer_to_server(
                RPCServerServicer(self), self._server)
            self._server.add_insecure_port('[::]:%d' % listen_port)
            self._server.start()
            self._started = True


    def stop(self):
        if not self._started:
            return

        with self._lock:
            self._server.stop(None).wait()
            del self._server
            self._started = False

    def check_auth_info(self, auth_info):
        project = Project.query.filter_by(
            name=auth_info.project_name).first()
        if project is None:
            raise UnauthorizedException('Invalid project')
        project_config = project.get_config()
        if project_config.token != auth_info.auth_token:
            raise UnauthorizedException('Invalid token')
        if project_config.domain_name != auth_info.target_domain:
            raise UnauthorizedException('Invalid domain')
        source_party = None
        for party in project_config.participants:
            if party.domain_name == auth_info.source_domain:
                source_party = party
        if source_party is None:
            raise UnauthorizedException('Invalid domain')
        return project, source_party

    def check_connection(self, request):
        _, _ = self.check_auth_info(request.auth_info)
        return service_pb2.CheckConnectionResponse(
            status=common_pb2.Status(
                code=common_pb2.STATUS_SUCCESS))

    def update_workflow_state(self, request):
        project, _ = self.check_auth_info(request.auth_info)
        name = request.workflow_name
        state = WorkflowState(request.state)
        target_state = WorkflowState(request.target_state)
        transaction_state = TransactionState(request.transaction_state)
        workflow = Workflow.query.filter_by(
            name=request.workflow_name,
            project_id=project.project_id).first()
        if workflow is None:
            assert state == WorkflowState.NEW
            assert target_state == WorkflowState.READY
            workflow = Workflow(
                name=request.workflow_name,
                state=state, target_state=target_state,
                transaction_state=TransactionState.READY)
            db.session.add(workflow)
            db.session.commit()
            workflow = Workflow.query.filter_by(
                name=request.workflow_name,
                project_id=project.project_id).first()
            assert workflow is not None

        tm = TransactionManager(workflow.workflow_id)
        ret = tm.update_workflow_state(
            state, target_state, transaction_state)
        return service_pb2.UpdateWorkflowStateResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS),
                transaction_state=ret.value)


rpc_server = RpcServer()

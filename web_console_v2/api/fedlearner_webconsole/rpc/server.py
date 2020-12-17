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

import threading
from concurrent import futures
import grpc
from fedlearner_webconsole.proto import (
    service_pb2, service_pb2_grpc, common_pb2
)
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.workflow.models import WorkflowStatus
from fedlearner_webconsole.workflow.apis import lock_workflow, release_workflow

workflow_status_map = {
    WorkflowStatus.CREATED: [WorkflowStatus.CREATE_SENDER_COMMITTABLE]}
workflow_finished_map = {
    WorkflowStatus.CREATED: [WorkflowStatus.CREATED]
}

class RPCServerServicer(service_pb2_grpc.WebConsoleV2ServiceServicer):
    def __init__(self, server):
        self._server = server

    def CheckConnection(self, request, context):
        try:
            return self._server.check_connection(request)
        except Exception as e:
            return service_pb2.CheckConnectionResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR,
                    msg=repr(e)))

    def UpdateWorkflow(self, request, context):
        try:
            return self._server.update_workflow(request)
        except Exception as e:
            return service_pb2.UpdateWorkflowResponse(
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
            return False
        fed_proto = project.get_config()
        if fed_proto.self_name != auth_info.receiver_name:
            return False
        if auth_info.sender_name not in fed_proto.participants:
            return False
        party = fed_proto.participants[auth_info.sender_name]
        if party.receiver_auth_token != auth_info.auth_token:
            return False
        return True

    def check_connection(self, request):
        if self.check_auth_info(request.auth_info):
            return service_pb2.CheckConnectionResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS))
        return service_pb2.CheckConnectionResponse(
            status=common_pb2.Status(
                code=common_pb2.STATUS_UNAUTHORIZED))

    def _create_workflow(self, request, workflow):
        if workflow is not None:
            return service_pb2.UpdateWorkflowResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS,
                    msg='Workflow has already existed'))
        new_name = '{}_受邀'.format(request.name)
        if Workflow.query.filter_by(name=new_name).first() is not None:
            return service_pb2.UpdateWorkflowResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS,
                    msg='Workflow has conflict name'))
        workflow = Workflow(uid=request.uid,
                            status=WorkflowStatus(request.status),
                            project_name=request.auth_info.project_name,
                            name=new_name, forkable=request.forkable,
                            config=request.config,
                            peer_config=request.peer_config)
        db.session.add(workflow)
        db.session.commit()
        return service_pb2.UpdateWorkflowResponse(
            status=common_pb2.Status(
                code=common_pb2.STATUS_SUCCESS,
                msg='Workflow created'))

    def update_workflow(self, request):

        if not self.check_auth_info(request.auth_info):
            return service_pb2.UpdateWorkflowResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNAUTHORIZED))
        workflow = Workflow.query.filter_by(uid=request.uid).first()
        if request.method_type in ['create', 'fork']:
            # TODO: when fork combine origin
            #  definition to protect PRIVATE Variable
            return self._create_workflow(request, workflow)

        if workflow is None:
            return service_pb2.UpdateWorkflowResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR,
                    msg='Workflow not existed'))
        status = WorkflowStatus(request.status)
        if workflow.status in workflow_finished_map[status]:
            return service_pb2.UpdateWorkflowResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS,
                    msg='Workflow has already updated'))
        lock_workflow(workflow, workflow_status_map[status])
        workflow.status = request.status
        workflow.forkable = request.forkable
        workflow.peer_config = workflow.peer_config
        db.session.commit()
        release_workflow(workflow)
        return service_pb2.UpdateWorkflowResponse(
            status=common_pb2.Status(
                code=common_pb2.STATUS_SUCCESS,
                msg='Workflow updated'))





rpc_server = RpcServer()

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
import time
import logging
import json
import os
import threading
from concurrent import futures
import grpc
from fedlearner_webconsole.proto import (
    service_pb2, service_pb2_grpc,
    common_pb2
)
from fedlearner_webconsole.utils.es import es
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.workflow.models import (
    Workflow, WorkflowState, TransactionState,
    _merge_workflow_config
)

from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.job.metrics import JobMetricsBuilder
from fedlearner_webconsole.exceptions import (
    UnauthorizedException
)

class RPCServerServicer(service_pb2_grpc.WebConsoleV2ServiceServicer):
    def __init__(self, server):
        self._server = server

    def CheckConnection(self, request, context):
        try:
            return self._server.check_connection(request, context)
        except UnauthorizedException as e:
            return service_pb2.CheckConnectionResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNAUTHORIZED,
                    msg=repr(e)))
        except Exception as e:
            logging.error('CheckConnection rpc server error: %s', repr(e))
            return service_pb2.CheckConnectionResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR,
                    msg=repr(e)))

    def UpdateWorkflowState(self, request, context):
        try:
            return self._server.update_workflow_state(request, context)
        except UnauthorizedException as e:
            return service_pb2.UpdateWorkflowStateResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNAUTHORIZED,
                    msg=repr(e)))
        except Exception as e:
            logging.error('UpdateWorkflowState rpc server error: %s', repr(e))
            return service_pb2.UpdateWorkflowStateResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR,
                    msg=repr(e)))

    def GetWorkflow(self, request, context):
        try:
            return self._server.get_workflow(request, context)
        except UnauthorizedException as e:
            return service_pb2.GetWorkflowResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNAUTHORIZED,
                    msg=repr(e)))
        except Exception as e:
            logging.error('GetWorkflow rpc server error: %s', repr(e))
            return service_pb2.GetWorkflowResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR,
                    msg=repr(e)))

    def UpdateWorkflow(self, request, context):
        try:
            return self._server.update_workflow(request, context)
        except UnauthorizedException as e:
            return service_pb2.UpdateWorkflowResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNAUTHORIZED,
                    msg=repr(e)))
        except Exception as e:
            logging.error('UpdateWorkflow rpc server error: %s', repr(e))
            return service_pb2.UpdateWorkflowResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR,
                    msg=repr(e)))

    def GetJobMetrics(self, request, context):
        try:
            return self._server.get_job_metrics(request, context)
        except UnauthorizedException as e:
            return service_pb2.GetJobMetricsResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNAUTHORIZED,
                    msg=repr(e)))
        except Exception as e:
            logging.error('GetJobMetrics rpc server error: %s', repr(e))
            return service_pb2.GetJobMetricsResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR,
                    msg=repr(e)))

    def GetJobEvents(self, request, context):
        try:
            return self._server.get_job_events(request, context)
        except UnauthorizedException as e:
            return service_pb2.GetJobEventsResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNAUTHORIZED,
                    msg=repr(e)))
        except Exception as e:
            logging.error('GetJobMetrics rpc server error: %s', repr(e))
            return service_pb2.GetJobEventsResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR,
                    msg=repr(e)))


class RpcServer(object):
    def __init__(self):
        self._lock = threading.Lock()
        self._started = False
        self._server = None
        self._app = None

    def start(self, app):
        assert not self._started, "Already started"
        self._app = app
        listen_port = app.config.get('GRPC_LISTEN_PORT', 1999)
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

    def check_auth_info(self, auth_info, context):
        logging.debug('auth_info: %s', auth_info)
        project = Project.query.filter_by(
            name=auth_info.project_name).first()
        if project is None:
            raise UnauthorizedException('Invalid project')
        project_config = project.get_config()
        # TODO: fix token verification
        # if project_config.token != auth_info.auth_token:
        #     raise UnauthorizedException('Invalid token')

        # Use first participant to mock for unit test
        # TODO: Fix for multi-peer
        source_party = project_config.participants[0]
        if os.environ.get('FLASK_ENV') == 'production':
            metadata = dict(context.invocation_metadata())
            # ssl-client-subject-dn example:
            # CN=*.fl-xxx.com,OU=security,O=security,L=beijing,ST=beijing,C=CN
            cn = metadata.get('ssl-client-subject-dn').split(',')[0][5:]
            for party in project_config.participants:
                if party.domain_name == cn:
                    source_party = party
            if source_party is None:
                raise UnauthorizedException('Invalid domain')
        return project, source_party

    def check_connection(self, request, context):
        with self._app.app_context():
            _, party = self.check_auth_info(request.auth_info, context)
            logging.debug(
                'received check_connection from %s', party.domain_name)
            return service_pb2.CheckConnectionResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS))

    def update_workflow_state(self, request, context):
        with self._app.app_context():
            project, party = self.check_auth_info(request.auth_info, context)
            logging.debug(
                'received update_workflow_state from %s: %s',
                party.domain_name, request)
            name = request.workflow_name
            uuid = request.uuid
            forked_from_uuid = request.forked_from_uuid
            forked_from = Workflow.query.filter_by(
                uuid=forked_from_uuid).first().id if forked_from_uuid else None
            state = WorkflowState(request.state)
            target_state = WorkflowState(request.target_state)
            transaction_state = TransactionState(request.transaction_state)
            workflow = Workflow.query.filter_by(
                name=request.workflow_name,
                project_id=project.id).first()
            if workflow is None:
                assert state == WorkflowState.NEW
                assert target_state == WorkflowState.READY
                workflow = Workflow(
                    name=name,
                    project_id=project.id,
                    state=state, target_state=target_state,
                    transaction_state=transaction_state,
                    uuid=uuid,
                    forked_from=forked_from
                )
                db.session.add(workflow)
                db.session.commit()
                db.session.refresh(workflow)

            workflow.update_state(
                state, target_state, transaction_state)
            db.session.commit()
            return service_pb2.UpdateWorkflowStateResponse(
                    status=common_pb2.Status(
                        code=common_pb2.STATUS_SUCCESS),
                    state=workflow.state.value,
                    target_state=workflow.target_state.value,
                    transaction_state=workflow.transaction_state.value)

    def _filter_workflow(self, workflow, modes):
        # filter peer-readable and peer-writable variables
        if workflow is None:
            return
        var_list = [
            i for i in workflow.variables if i.access_mode in modes]
        workflow.ClearField('variables')
        for i in var_list:
            workflow.variables.append(i)
        for job_def in workflow.job_definitions:
            var_list = [
                i for i in job_def.variables if i.access_mode in modes]
            job_def.ClearField('variables')
            for i in var_list:
                job_def.variables.append(i)

    def get_workflow(self, request, context):
        with self._app.app_context():
            project, party = self.check_auth_info(request.auth_info, context)
            workflow = Workflow.query.filter_by(
                name=request.workflow_name,
                project_id=project.id).first()
            assert workflow is not None, "Workflow not found"
            config = workflow.get_config()
            self._filter_workflow(
                config,
                [
                    common_pb2.Variable.PEER_READABLE,
                    common_pb2.Variable.PEER_WRITABLE
                ])
            # job details
            jobs = [service_pb2.JobDetail(
                name=job.name,
                state=job.get_state_for_frontend(),
                pods=json.dumps(job.get_pods_for_frontend()))
                for job in workflow.get_jobs()]
            # fork info
            forked_from = ''
            if workflow.forked_from:
                forked_from = Workflow.query.get(workflow.forked_from).name
            return service_pb2.GetWorkflowResponse(
                name=request.workflow_name,
                status=common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS),
                config=config,
                jobs=jobs,
                state=workflow.state.value,
                target_state=workflow.target_state.value,
                transaction_state=workflow.transaction_state.value,
                forkable=workflow.forkable,
                forked_from=forked_from,
                reuse_job_names=workflow.get_reuse_job_names(),
                peer_reuse_job_names=workflow.get_peer_reuse_job_names(),
                fork_proposal_config=workflow.get_fork_proposal_config(),
                uuid=workflow.uuid
            )

    def update_workflow(self, request, context):
        with self._app.app_context():
            project, party = self.check_auth_info(request.auth_info, context)
            workflow = Workflow.query.filter_by(
                name=request.workflow_name,
                project_id=project.id).first()
            assert workflow is not None, "Workflow not found"
            config = workflow.get_config()
            _merge_workflow_config(
                config, request.config,
                [common_pb2.Variable.PEER_WRITABLE])
            workflow.set_config(config)
            db.session.commit()

            self._filter_workflow(
                config,
                [
                    common_pb2.Variable.PEER_READABLE,
                    common_pb2.Variable.PEER_WRITABLE
                ])
            return service_pb2.UpdateWorkflowResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS),
                workflow_name=request.workflow_name,
                config=config)

    def get_job_metrics(self, request, context):
        with self._app.app_context():
            project, party = self.check_auth_info(request.auth_info, context)
            job = Job.query.filter_by(name=request.job_name,
                                      project_id=project.id).first()
            assert job is not None, f'Job {request.job_name} not found'
            workflow = job.workflow
            if not workflow.metric_is_public:
                raise UnauthorizedException('Metric is private!')
            metrics = JobMetricsBuilder(job).plot_metrics()
            return service_pb2.GetJobMetricsResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS),
                metrics=json.dumps(metrics))

    def get_job_events(self, request, context):
        with self._app.app_context():
            project, party = self.check_auth_info(request.auth_info, context)
            job = Job.query.filter_by(name=request.job_name,
                                      project_id=project.id).first
            assert job is not None, \
                f'Job {request.job_name} not found'

            result = es.query_events('filebeat-*', job.name,
                                     'fedlearner-operator',
                                     request.start_time,
                                     int(time.time() * 1000)
                                     )[:request.max_lines][::-1]

            return service_pb2.GetJobEventsResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS),
                logs=result)


rpc_server = RpcServer()

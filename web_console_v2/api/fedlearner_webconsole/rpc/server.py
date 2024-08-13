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
# pylint: disable=broad-except
from datetime import timedelta
import inspect
import time
import logging
import json
import sys
import threading
import traceback
from concurrent import futures
from functools import wraps
from envs import Envs

import grpc
from grpc_reflection.v1alpha import reflection
from google.protobuf import empty_pb2
from google.protobuf.wrappers_pb2 import BoolValue
from fedlearner_webconsole.middleware.request_id import GrpcRequestIdMiddleware
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.proto import (dataset_pb2, service_pb2, service_pb2_grpc, common_pb2,
                                         workflow_definition_pb2)
from fedlearner_webconsole.proto.review_pb2 import ReviewStatus
from fedlearner_webconsole.proto.rpc.v2 import system_service_pb2_grpc, system_service_pb2, project_service_pb2_grpc
from fedlearner_webconsole.proto.service_pb2 import (TwoPcRequest, TwoPcResponse)
from fedlearner_webconsole.review.ticket_helper import get_ticket_helper
from fedlearner_webconsole.review.common import NO_CENTRAL_SERVER_UUID
from fedlearner_webconsole.rpc.auth import get_common_name
from fedlearner_webconsole.rpc.v2.system_service_server import SystemGrpcService
from fedlearner_webconsole.serving.services import NegotiatorServingService
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.two_pc.handlers import run_two_pc_action
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.domain_name import get_pure_domain_name
from fedlearner_webconsole.utils.es import es
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.kibana import Kibana
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.workflow.models import (Workflow, WorkflowState, TransactionState)
from fedlearner_webconsole.workflow.resource_manager import \
    merge_workflow_config, ResourceManager
from fedlearner_webconsole.workflow.service import WorkflowService
from fedlearner_webconsole.workflow.workflow_controller import invalidate_workflow_locally
from fedlearner_webconsole.utils.pp_datetime import now
from fedlearner_webconsole.utils.proto import to_json, to_dict
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.job.service import JobService
from fedlearner_webconsole.job.metrics import JobMetricsBuilder
from fedlearner_webconsole.mmgr.models import ModelJobGroup
from fedlearner_webconsole.exceptions import (UnauthorizedException, InvalidArgumentException)
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.mmgr.models import ModelJob
from fedlearner_webconsole.mmgr.service import ModelJobService
from fedlearner_webconsole.dataset.services import DatasetService, DatasetJobService, BatchService
from fedlearner_webconsole.dataset.models import DatasetJob, DatasetJobKind, \
    Dataset, ProcessedDataset, DatasetKindV2, DatasetFormat, ResourceState
from fedlearner_webconsole.dataset.auth_service import AuthService
from fedlearner_webconsole.dataset.job_configer.dataset_job_configer import DatasetJobConfiger
from fedlearner_webconsole.proto.rpc.v2 import job_service_pb2_grpc, job_service_pb2, resource_service_pb2_grpc,\
    resource_service_pb2
from fedlearner_webconsole.rpc.v2.auth_server_interceptor import AuthServerInterceptor
from fedlearner_webconsole.rpc.v2.job_service_server import JobServiceServicer
from fedlearner_webconsole.rpc.v2.resource_service_server import ResourceServiceServicer
from fedlearner_webconsole.rpc.v2.project_service_server import ProjectGrpcService
from fedlearner_webconsole.flag.models import Flag
from fedlearner_webconsole.audit.decorators import emits_rpc_event, get_two_pc_request_uuid


def _set_request_id_for_all_methods():
    """A hack way to wrap all gRPC methods to set request id in context.

    Why not service interceptor?
    The request id is attached on thread local, but interceptor is not sharing
    the same thread with service handler, we are not able to set the context on
    thread local in interceptor as it will not work in service handler."""

    def set_request_id_in_context(fn):

        @wraps(fn)
        def wrapper(self, request, context):
            GrpcRequestIdMiddleware.set_request_id_in_context(context)
            return fn(self, request, context)

        return wrapper

    def decorate(cls):
        # A hack to get all methods
        grpc_methods = service_pb2.DESCRIPTOR.services_by_name['WebConsoleV2Service'].methods_by_name
        for name, fn in inspect.getmembers(cls, inspect.isfunction):
            # If this is a gRPC method
            if name in grpc_methods:
                setattr(cls, name, set_request_id_in_context(fn))
        return cls

    return decorate


@_set_request_id_for_all_methods()
class RPCServerServicer(service_pb2_grpc.WebConsoleV2ServiceServicer):

    def __init__(self, server):
        self._server = server

    def _secure_exc(self):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        # filter out exc_obj to protect sensitive info
        secure_exc = f'Error {exc_type} at '
        secure_exc += ''.join(traceback.format_tb(exc_tb))
        return secure_exc

    def _try_handle_request(self, func, request, context, resp_class):
        try:
            return func(request, context)
        except UnauthorizedException as e:
            return resp_class(status=common_pb2.Status(code=common_pb2.STATUS_UNAUTHORIZED,
                                                       msg=f'Invalid auth: {repr(request.auth_info)}'))
        except Exception as e:
            logging.error('%s rpc server error: %s', func.__name__, repr(e))
            return resp_class(status=common_pb2.Status(code=common_pb2.STATUS_UNKNOWN_ERROR, msg=self._secure_exc()))

    def CheckConnection(self, request, context):
        return self._try_handle_request(self._server.check_connection, request, context,
                                        service_pb2.CheckConnectionResponse)

    def CheckPeerConnection(self, request, context):
        return self._try_handle_request(self._server.check_peer_connection, request, context,
                                        service_pb2.CheckPeerConnectionResponse)

    @emits_rpc_event(resource_type=Event.ResourceType.WORKFLOW,
                     op_type=Event.OperationType.UPDATE_STATE,
                     resource_name_fn=lambda request: request.uuid)
    def UpdateWorkflowState(self, request, context):
        return self._try_handle_request(self._server.update_workflow_state, request, context,
                                        service_pb2.UpdateWorkflowStateResponse)

    def GetWorkflow(self, request, context):
        return self._try_handle_request(self._server.get_workflow, request, context, service_pb2.GetWorkflowResponse)

    @emits_rpc_event(resource_type=Event.ResourceType.WORKFLOW,
                     op_type=Event.OperationType.UPDATE,
                     resource_name_fn=lambda request: request.workflow_uuid)
    def UpdateWorkflow(self, request, context):
        return self._try_handle_request(self._server.update_workflow, request, context,
                                        service_pb2.UpdateWorkflowResponse)

    @emits_rpc_event(resource_type=Event.ResourceType.WORKFLOW,
                     op_type=Event.OperationType.INVALIDATE,
                     resource_name_fn=lambda request: request.workflow_uuid)
    def InvalidateWorkflow(self, request, context):
        return self._try_handle_request(self._server.invalidate_workflow, request, context,
                                        service_pb2.InvalidateWorkflowResponse)

    def GetJobMetrics(self, request, context):
        return self._try_handle_request(self._server.get_job_metrics, request, context,
                                        service_pb2.GetJobMetricsResponse)

    def GetJobKibana(self, request, context):
        return self._try_handle_request(self._server.get_job_kibana, request, context, service_pb2.GetJobKibanaResponse)

    def GetJobEvents(self, request, context):
        return self._try_handle_request(self._server.get_job_events, request, context, service_pb2.GetJobEventsResponse)

    def CheckJobReady(self, request, context):
        return self._try_handle_request(self._server.check_job_ready, request, context,
                                        service_pb2.CheckJobReadyResponse)

    def _run_2pc(self, request: TwoPcRequest, context: grpc.ServicerContext) -> TwoPcResponse:
        with db.session_scope() as session:
            project, _ = self._server.check_auth_info(request.auth_info, context, session)
            succeeded, message = run_two_pc_action(session=session,
                                                   tid=request.transaction_uuid,
                                                   two_pc_type=request.type,
                                                   action=request.action,
                                                   data=request.data)
            session.commit()
        return TwoPcResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                             transaction_uuid=request.transaction_uuid,
                             type=request.type,
                             action=request.action,
                             succeeded=succeeded,
                             message=message)

    @emits_rpc_event(resource_type=Event.ResourceType.UNKNOWN_RESOURCE_TYPE,
                     op_type=Event.OperationType.UNKNOWN_OPERATION_TYPE,
                     resource_name_fn=get_two_pc_request_uuid)
    def Run2Pc(self, request: TwoPcRequest, context: grpc.ServicerContext):
        return self._try_handle_request(self._run_2pc, request, context, service_pb2.TwoPcResponse)

    @emits_rpc_event(resource_type=Event.ResourceType.SERVING_SERVICE,
                     op_type=Event.OperationType.OPERATE,
                     resource_name_fn=lambda request: request.serving_model_uuid)
    def ServingServiceManagement(self, request: service_pb2.ServingServiceRequest,
                                 context: grpc.ServicerContext) -> service_pb2.ServingServiceResponse:
        return self._try_handle_request(self._server.operate_serving_service, request, context,
                                        service_pb2.ServingServiceResponse)

    @emits_rpc_event(resource_type=Event.ResourceType.SERVING_SERVICE,
                     op_type=Event.OperationType.INFERENCE,
                     resource_name_fn=lambda request: request.serving_model_uuid)
    def ServingServiceInference(self, request: service_pb2.ServingServiceInferenceRequest,
                                context: grpc.ServicerContext) -> service_pb2.ServingServiceInferenceResponse:
        return self._try_handle_request(self._server.inference_serving_service, request, context,
                                        service_pb2.ServingServiceInferenceResponse)

    def ClientHeartBeat(self, request, context):
        return self._server.client_heart_beat(request, context)

    def GetModelJob(self, request, context):
        return self._server.get_model_job(request, context)

    def GetModelJobGroup(self, request, context):
        return self._server.get_model_job_group(request, context)

    @emits_rpc_event(resource_type=Event.ResourceType.MODEL_JOB_GROUP,
                     op_type=Event.OperationType.UPDATE,
                     resource_name_fn=lambda request: request.uuid)
    def UpdateModelJobGroup(self, request, context):
        return self._server.update_model_job_group(request, context)

    def ListParticipantDatasets(self, request, context):
        return self._server.list_participant_datasets(request, context)

    def GetDatasetJob(self, request: service_pb2.GetDatasetJobRequest,
                      context: grpc.ServicerContext) -> service_pb2.GetDatasetJobResponse:
        return self._server.get_dataset_job(request, context)

    @emits_rpc_event(resource_type=Event.ResourceType.DATASET_JOB,
                     op_type=Event.OperationType.CREATE,
                     resource_name_fn=lambda request: request.dataset_job.uuid)
    def CreateDatasetJob(self, request: service_pb2.CreateDatasetJobRequest,
                         context: grpc.ServicerContext) -> empty_pb2.Empty:
        return self._server.create_dataset_job(request, context)


# TODO(wangsen.0914): make the rpc server clean, move business logic out
class RpcServer(object):

    def __init__(self):
        self.started = False
        self._lock = threading.Lock()
        self._server = None

    def start(self, port: int):
        assert not self.started, 'Already started'
        with self._lock:
            self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=30),
                                       interceptors=[AuthServerInterceptor()])
            service_pb2_grpc.add_WebConsoleV2ServiceServicer_to_server(RPCServerServicer(self), self._server)
            system_service_pb2_grpc.add_SystemServiceServicer_to_server(SystemGrpcService(), self._server)
            job_service_pb2_grpc.add_JobServiceServicer_to_server(JobServiceServicer(), self._server)
            resource_service_pb2_grpc.add_ResourceServiceServicer_to_server(ResourceServiceServicer(), self._server)
            project_service_pb2_grpc.add_ProjectServiceServicer_to_server(ProjectGrpcService(), self._server)
            # reflection supports server find service by using url, e.g. /SystemService.CheckHealth
            reflection.enable_server_reflection(service_pb2.DESCRIPTOR.services_by_name, self._server)
            reflection.enable_server_reflection(system_service_pb2.DESCRIPTOR.services_by_name, self._server)
            reflection.enable_server_reflection(job_service_pb2.DESCRIPTOR.services_by_name, self._server)
            reflection.enable_server_reflection(resource_service_pb2.DESCRIPTOR.services_by_name, self._server)
            self._server.add_insecure_port(f'[::]:{port}')
            self._server.start()
            self.started = True

    def stop(self):
        if not self.started:
            return

        with self._lock:
            self._server.stop(None).wait()
            del self._server
            self.started = False

    def check_auth_info(self, auth_info, context, session):
        logging.debug('auth_info: %s', auth_info)
        project = session.query(Project).filter_by(name=auth_info.project_name).first()
        if project is None:
            raise UnauthorizedException(f'Invalid project {auth_info.project_name}')
        # TODO: fix token verification
        # if project_config.token != auth_info.auth_token:
        #     raise UnauthorizedException('Invalid token')

        service = ParticipantService(session)
        participants = service.get_participants_by_project(project.id)
        # TODO: Fix for multi-peer
        source_party = participants[0]
        if Envs.FLASK_ENV == 'production':
            source_party = None
            metadata = dict(context.invocation_metadata())
            cn = get_common_name(metadata.get('ssl-client-subject-dn'))
            if not cn:
                raise UnauthorizedException('Failed to get domain name from certs')
            pure_domain_name = get_pure_domain_name(cn)
            for party in participants:
                if get_pure_domain_name(party.domain_name) == pure_domain_name:
                    source_party = party
            if source_party is None:
                raise UnauthorizedException(f'Invalid domain {pure_domain_name}')
        return project, source_party

    def check_connection(self, request, context):
        with db.session_scope() as session:
            _, party = self.check_auth_info(request.auth_info, context, session)
            logging.debug('received check_connection from %s', party.domain_name)
            return service_pb2.CheckConnectionResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS))

    def check_peer_connection(self, request, context):
        logging.debug('received request: check peer connection')
        with db.session_scope() as session:
            service = SettingService(session)
            version = service.get_application_version()
        return service_pb2.CheckPeerConnectionResponse(status=common_pb2.Status(
            code=common_pb2.STATUS_SUCCESS, msg='participant received check request successfully!'),
                                                       application_version=version.to_proto())

    def update_workflow_state(self, request, context):
        with db.session_scope() as session:
            project, party = self.check_auth_info(request.auth_info, context, session)
            logging.debug('received update_workflow_state from %s: %s', party.domain_name, request)
            name = request.workflow_name
            uuid = request.uuid
            forked_from_uuid = request.forked_from_uuid
            forked_from = session.query(Workflow).filter_by(
                uuid=forked_from_uuid).first().id if forked_from_uuid else None
            state = WorkflowState(request.state)
            target_state = WorkflowState(request.target_state)
            transaction_state = TransactionState(request.transaction_state)
            workflow = session.query(Workflow).filter_by(name=request.workflow_name, project_id=project.id).first()
            if workflow is None:
                assert state == WorkflowState.NEW
                assert target_state == WorkflowState.READY
                workflow = Workflow(name=name,
                                    project_id=project.id,
                                    state=state,
                                    target_state=target_state,
                                    transaction_state=transaction_state,
                                    uuid=uuid,
                                    forked_from=forked_from,
                                    extra=request.extra)
                session.add(workflow)
                session.commit()
                session.refresh(workflow)

            ResourceManager(session, workflow).update_state(state, target_state, transaction_state)
            session.commit()
            return service_pb2.UpdateWorkflowStateResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                           state=workflow.state.value,
                                                           target_state=workflow.target_state.value,
                                                           transaction_state=workflow.transaction_state.value)

    def _filter_workflow(self, workflow, modes):
        # filter peer-readable and peer-writable variables
        if workflow is None:
            return None

        new_wf = workflow_definition_pb2.WorkflowDefinition(group_alias=workflow.group_alias)
        for var in workflow.variables:
            if var.access_mode in modes:
                new_wf.variables.append(var)
        for job_def in workflow.job_definitions:
            # keep yaml template private
            new_jd = workflow_definition_pb2.JobDefinition(name=job_def.name,
                                                           job_type=job_def.job_type,
                                                           is_federated=job_def.is_federated,
                                                           dependencies=job_def.dependencies)
            for var in job_def.variables:
                if var.access_mode in modes:
                    new_jd.variables.append(var)
            new_wf.job_definitions.append(new_jd)
        return new_wf

    def get_workflow(self, request, context):
        with db.session_scope() as session:
            project, party = self.check_auth_info(request.auth_info, context, session)
            # TODO(hangweiqiang): remove workflow name
            # compatible method for previous version
            if request.workflow_uuid:
                workflow = session.query(Workflow).filter_by(uuid=request.workflow_uuid, project_id=project.id).first()
            else:
                workflow = session.query(Workflow).filter_by(name=request.workflow_name, project_id=project.id).first()
            assert workflow is not None, 'Workflow not found'
            config = workflow.get_config()
            config = self._filter_workflow(config,
                                           [common_pb2.Variable.PEER_READABLE, common_pb2.Variable.PEER_WRITABLE])
            # job details
            jobs = [
                service_pb2.JobDetail(
                    name=job.name,
                    state=job.state.name,
                    created_at=to_timestamp(job.created_at),
                    pods=json.dumps([to_dict(pod)
                                     for pod in JobService.get_pods(job, include_private_info=False)]))
                for job in workflow.get_jobs(session)
            ]
            # fork info
            forked_from = ''
            if workflow.forked_from:
                forked_from = session.query(Workflow).get(workflow.forked_from).name
            return service_pb2.GetWorkflowResponse(name=workflow.name,
                                                   status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                   config=config,
                                                   jobs=jobs,
                                                   state=workflow.state.value,
                                                   target_state=workflow.target_state.value,
                                                   transaction_state=workflow.transaction_state.value,
                                                   forkable=workflow.forkable,
                                                   forked_from=forked_from,
                                                   create_job_flags=workflow.get_create_job_flags(),
                                                   peer_create_job_flags=workflow.get_peer_create_job_flags(),
                                                   fork_proposal_config=workflow.get_fork_proposal_config(),
                                                   uuid=workflow.uuid,
                                                   metric_is_public=workflow.metric_is_public,
                                                   is_finished=workflow.is_finished())

    def update_workflow(self, request, context):
        with db.session_scope() as session:
            project, party = self.check_auth_info(request.auth_info, context, session)
            # TODO(hangweiqiang): remove workflow name
            # compatible method for previous version
            if request.workflow_uuid:
                workflow = session.query(Workflow).filter_by(uuid=request.workflow_uuid, project_id=project.id).first()
            else:
                workflow = session.query(Workflow).filter_by(name=request.workflow_name, project_id=project.id).first()
            assert workflow is not None, 'Workflow not found'
            config = workflow.get_config()
            merge_workflow_config(config, request.config, [common_pb2.Variable.PEER_WRITABLE])
            WorkflowService(session).update_config(workflow, config)
            session.commit()

            config = self._filter_workflow(config,
                                           [common_pb2.Variable.PEER_READABLE, common_pb2.Variable.PEER_WRITABLE])
            # compatible method for previous version
            if request.workflow_uuid:
                return service_pb2.UpdateWorkflowResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                          workflow_uuid=request.workflow_uuid,
                                                          config=config)
            return service_pb2.UpdateWorkflowResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                      workflow_name=request.workflow_name,
                                                      config=config)

    def invalidate_workflow(self, request, context):
        with db.session_scope() as session:
            project, party = self.check_auth_info(request.auth_info, context, session)
            workflow = session.query(Workflow).filter_by(uuid=request.workflow_uuid, project_id=project.id).first()
            if workflow is None:
                logging.error(f'Failed to find workflow: {request.workflow_uuid}')
                return service_pb2.InvalidateWorkflowResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                              succeeded=False)
            invalidate_workflow_locally(session, workflow)
            session.commit()
            return service_pb2.InvalidateWorkflowResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                          succeeded=True)

    def _check_metrics_public(self, request, context):
        with db.session_scope() as session:
            project, party = self.check_auth_info(request.auth_info, context, session)
            job = session.query(Job).filter_by(name=request.job_name, project_id=project.id).first()
            assert job is not None, f'job {request.job_name} not found'
            workflow = job.workflow
            if not workflow.metric_is_public:
                raise UnauthorizedException('Metric is private!')
            return job

    def get_job_metrics(self, request, context):
        with db.session_scope():
            job = self._check_metrics_public(request, context)
            metrics = JobMetricsBuilder(job).plot_metrics()
            return service_pb2.GetJobMetricsResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                     metrics=json.dumps(metrics))

    def get_job_kibana(self, request, context):
        with db.session_scope():
            job = self._check_metrics_public(request, context)
            try:
                metrics = Kibana.remote_query(job, json.loads(request.json_args))
            except UnauthorizedException as ua_e:
                return service_pb2.GetJobKibanaResponse(
                    status=common_pb2.Status(code=common_pb2.STATUS_UNAUTHORIZED, msg=ua_e.message))
            except InvalidArgumentException as ia_e:
                return service_pb2.GetJobKibanaResponse(
                    status=common_pb2.Status(code=common_pb2.STATUS_INVALID_ARGUMENT, msg=ia_e.message))
            return service_pb2.GetJobKibanaResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                    metrics=json.dumps(metrics))

    def get_job_events(self, request, context):
        with db.session_scope() as session:
            project, party = self.check_auth_info(request.auth_info, context, session)
            job = session.query(Job).filter_by(name=request.job_name, project_id=project.id).first()
            assert job is not None, \
                f'Job {request.job_name} not found'

            result = es.query_events('filebeat-*', job.name, 'fedlearner-operator', request.start_time,
                                     int(time.time() * 1000), Envs.OPERATOR_LOG_MATCH_PHRASE)[:request.max_lines][::-1]

            return service_pb2.GetJobEventsResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                    logs=result)

    def check_job_ready(self, request, context):
        with db.session_scope() as session:
            project, _ = self.check_auth_info(request.auth_info, context, session)
            job = session.query(Job).filter_by(name=request.job_name, project_id=project.id).first()
            assert job is not None, \
                f'Job {request.job_name} not found'

            is_ready = JobService(session).is_ready(job)
            return service_pb2.CheckJobReadyResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                     is_ready=is_ready)

    def operate_serving_service(self, request, context) -> service_pb2.ServingServiceResponse:
        with db.session_scope() as session:
            project, _ = self.check_auth_info(request.auth_info, context, session)
            return NegotiatorServingService(session).handle_participant_request(request, project)

    def inference_serving_service(self, request, context) -> service_pb2.ServingServiceInferenceResponse:
        with db.session_scope() as session:
            project, _ = self.check_auth_info(request.auth_info, context, session)
            return NegotiatorServingService(session).handle_participant_inference_request(request, project)

    def client_heart_beat(self, request: service_pb2.ClientHeartBeatRequest, context):
        with db.session_scope() as session:
            party: Participant = session.query(Participant).filter_by(request.domain_name)
            if party is None:
                return service_pb2.ClientHeartBeatResponse(succeeded=False)
            party.last_connected_at = now()
            session.commit()
        return service_pb2.ClientHeartBeatResponse(succeeded=True)

    def get_model_job(self, request: service_pb2.GetModelJobRequest, context) -> service_pb2.GetModelJobResponse:
        with db.session_scope() as session:
            project, _ = self.check_auth_info(request.auth_info, context, session)
            model_job: ModelJob = session.query(ModelJob).filter_by(uuid=request.uuid).first()
            group_uuid = None
            if model_job.group:
                group_uuid = model_job.group.uuid
            config = model_job.workflow.get_config()
            config = self._filter_workflow(config,
                                           [common_pb2.Variable.PEER_READABLE, common_pb2.Variable.PEER_WRITABLE])
            metrics = None
            if request.need_metrics and model_job.job is not None and model_job.metric_is_public:
                metrics = to_json(ModelJobService(session).query_metrics(model_job))
            return service_pb2.GetModelJobResponse(name=model_job.name,
                                                   uuid=model_job.uuid,
                                                   algorithm_type=model_job.algorithm_type.name,
                                                   model_job_type=model_job.model_job_type.name,
                                                   state=model_job.state.name,
                                                   group_uuid=group_uuid,
                                                   config=config,
                                                   metrics=metrics,
                                                   metric_is_public=BoolValue(value=model_job.metric_is_public))

    def get_model_job_group(self, request: service_pb2.GetModelJobGroupRequest, context):
        with db.session_scope() as session:
            project, _ = self.check_auth_info(request.auth_info, context, session)
            group: ModelJobGroup = session.query(ModelJobGroup).filter_by(uuid=request.uuid).first()
            return service_pb2.GetModelJobGroupResponse(name=group.name,
                                                        uuid=group.uuid,
                                                        role=group.role.name,
                                                        authorized=group.authorized,
                                                        algorithm_type=group.algorithm_type.name,
                                                        config=group.get_config())

    def update_model_job_group(self, request: service_pb2.UpdateModelJobGroupRequest, context):
        with db.session_scope() as session:
            project, _ = self.check_auth_info(request.auth_info, context, session)
            group: ModelJobGroup = session.query(ModelJobGroup).filter_by(uuid=request.uuid).first()
            if not group.authorized:
                raise UnauthorizedException(f'group {group.name} is not authorized for editing')
            group.set_config(request.config)
            session.commit()
            return service_pb2.UpdateModelJobGroupResponse(uuid=group.uuid, config=group.get_config())

    # TODO(liuhehan): delete after all participants support new rpc
    def list_participant_datasets(self, request: service_pb2.ListParticipantDatasetsRequest, context):
        kind = DatasetKindV2(request.kind) if request.kind else None
        uuid = request.uuid if request.uuid else None
        state = ResourceState.SUCCEEDED
        with db.session_scope() as session:
            project, _ = self.check_auth_info(request.auth_info, context, session)
            datasets = DatasetService(session=session).get_published_datasets(project.id, kind, uuid, state)
            return service_pb2.ListParticipantDatasetsResponse(participant_datasets=datasets)

    def get_dataset_job(self, request: service_pb2.GetDatasetJobRequest,
                        context: grpc.ServicerContext) -> service_pb2.GetDatasetJobResponse:
        with db.session_scope() as session:
            self.check_auth_info(request.auth_info, context, session)
            dataset_job_model = session.query(DatasetJob).filter(DatasetJob.uuid == request.uuid).first()
            if dataset_job_model is None:
                context.abort(code=grpc.StatusCode.NOT_FOUND, details=f'could not find dataset {request.uuid}')
            dataset_job = dataset_job_model.to_proto()
            dataset_job.workflow_definition.MergeFrom(
                DatasetJobConfiger.from_kind(dataset_job_model.kind, session).get_config())
            return service_pb2.GetDatasetJobResponse(dataset_job=dataset_job)

    def create_dataset_job(self, request: service_pb2.CreateDatasetJobRequest,
                           context: grpc.ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project, participant = self.check_auth_info(request.auth_info, context, session)

            # this is a hack to allow no ticket_uuid, delete it after all customers update
            ticket_uuid = request.ticket_uuid if request.ticket_uuid else NO_CENTRAL_SERVER_UUID
            ticket_helper = get_ticket_helper(session=session)
            validate = ticket_helper.validate_ticket(
                ticket_uuid, lambda ticket: ticket.details.uuid == request.dataset_job.result_dataset_uuid and ticket.
                status == ReviewStatus.APPROVED)
            if not validate:
                message = f'[create_dataset_job]: ticket status is not approved, ticket_uuid: {request.ticket_uuid}'
                logging.warning(message)
                context.abort(code=grpc.StatusCode.PERMISSION_DENIED, details=message)

            processed_dataset = session.query(ProcessedDataset).filter_by(
                uuid=request.dataset_job.result_dataset_uuid).first()
            if processed_dataset is None:
                # create processed dataset
                domain_name = SettingService.get_system_info().pure_domain_name
                dataset_job_config = request.dataset_job.global_configs.global_configs.get(domain_name)
                dataset = session.query(Dataset).filter_by(uuid=dataset_job_config.dataset_uuid).first()
                dataset_param = dataset_pb2.DatasetParameter(
                    name=request.dataset_job.result_dataset_name,
                    type=dataset.dataset_type.value,
                    project_id=project.id,
                    kind=DatasetKindV2.PROCESSED.value,
                    format=DatasetFormat(dataset.dataset_format).name,
                    uuid=request.dataset_job.result_dataset_uuid,
                    is_published=True,
                    creator_username=request.dataset.creator_username,
                )
                participants_info = request.dataset.participants_info
                if not Flag.DATASET_AUTH_STATUS_CHECK_ENABLED.value:
                    # auto set participant auth_status and cache to authorized if no need check
                    dataset_param.auth_status = AuthStatus.AUTHORIZED.name
                    participants_info.participants_map[domain_name].auth_status = AuthStatus.AUTHORIZED.name
                processed_dataset = DatasetService(session=session).create_dataset(dataset_param)
                processed_dataset.ticket_uuid = request.ticket_uuid
                processed_dataset.ticket_status = TicketStatus.APPROVED
                session.flush([processed_dataset])
                # old dataset job will create data_batch in grpc level
                # new dataset job will create data_batch before create dataset_job_stage
                if not request.dataset_job.has_stages:
                    batch_parameter = dataset_pb2.BatchParameter(dataset_id=processed_dataset.id)
                    BatchService(session).create_batch(batch_parameter)

            dataset_job = session.query(DatasetJob).filter_by(uuid=request.dataset_job.uuid).first()
            if dataset_job is None:
                time_range = timedelta(days=request.dataset_job.time_range.days,
                                       hours=request.dataset_job.time_range.hours)
                dataset_job = DatasetJobService(session=session).create_as_participant(
                    project_id=project.id,
                    kind=DatasetJobKind(request.dataset_job.kind),
                    global_configs=request.dataset_job.global_configs,
                    config=request.dataset_job.workflow_definition,
                    output_dataset_id=processed_dataset.id,
                    coordinator_id=participant.id,
                    uuid=request.dataset_job.uuid,
                    creator_username=request.dataset_job.creator_username,
                    time_range=time_range if time_range else None)
            session.flush()
            AuthService(session=session, dataset_job=dataset_job).initialize_participants_info_as_participant(
                participants_info=request.dataset.participants_info)

            session.commit()
            return empty_pb2.Empty()

    def wait_for_termination(self):
        if not self.started:
            logging.warning('gRPC service is not yet started, failed to wait')
        self._server.wait_for_termination()


rpc_server = RpcServer()

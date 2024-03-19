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

import logging
from typing import Dict

import grpc
from google.protobuf import empty_pb2
from grpc import ServicerContext

from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import PendingProjectState, ProjectRole, PendingProject, Project
from fedlearner_webconsole.project.services import PendingProjectService
from fedlearner_webconsole.proto.project_pb2 import ParticipantInfo, ParticipantsInfo
from fedlearner_webconsole.proto.rpc.v2.project_service_pb2_grpc import ProjectServiceServicer
from fedlearner_webconsole.proto.rpc.v2.project_service_pb2 import CreatePendingProjectRequest, \
    UpdatePendingProjectRequest, SyncPendingProjectStateRequest, CreateProjectRequest, SendTemplateRevisionRequest
from fedlearner_webconsole.review.ticket_helper import get_ticket_helper
from fedlearner_webconsole.rpc.v2.utils import get_pure_domain_from_context
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.pp_datetime import now
from fedlearner_webconsole.workflow_template.service import WorkflowTemplateRevisionService
from fedlearner_webconsole.audit.decorators import emits_rpc_event
from fedlearner_webconsole.proto.audit_pb2 import Event


def _is_same_participants(participants_map: Dict[str, ParticipantInfo],
                          new_participants_map: Dict[str, ParticipantInfo]) -> bool:
    return set(participants_map) != set(new_participants_map)


class ProjectGrpcService(ProjectServiceServicer):

    @emits_rpc_event(resource_type=Event.ResourceType.PENDING_PROJECT,
                     op_type=Event.OperationType.CREATE,
                     resource_name_fn=lambda request: request.uuid)
    def CreatePendingProject(self, request: CreatePendingProjectRequest, context: ServicerContext):

        with db.session_scope() as session:
            existed = session.query(PendingProject).filter_by(uuid=request.uuid).first()
            # make CreatePendingProject idempotent
            if existed is not None:
                return empty_pb2.Empty()
            validate = get_ticket_helper(session).validate_ticket(request.ticket_uuid,
                                                                  lambda ticket: ticket.details.uuid == request.uuid)
            if not validate:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, f'ticket {request.ticket_uuid} is not validated')
            pending_project = PendingProjectService(session).create_pending_project(
                name=request.name,
                config=request.config,
                participants_info=request.participants_info,
                comment=request.comment,
                uuid=request.uuid,
                creator_username=request.creator_username,
                state=PendingProjectState.PENDING,
                role=ProjectRole.PARTICIPANT)
            pending_project.ticket_uuid = request.ticket_uuid
            pending_project.ticket_status = TicketStatus.APPROVED
            session.commit()
        return empty_pb2.Empty()

    @emits_rpc_event(resource_type=Event.ResourceType.PENDING_PROJECT,
                     op_type=Event.OperationType.UPDATE,
                     resource_name_fn=lambda request: request.uuid)
    def UpdatePendingProject(self, request: UpdatePendingProjectRequest, context: ServicerContext):
        peer_pure_domain = get_pure_domain_from_context(context)
        with db.session_scope() as session:
            # we set isolation_level to SERIALIZABLE to make sure participants_info won't be changed within this session
            session.connection(execution_options={'isolation_level': 'SERIALIZABLE'})
            pending_project: PendingProject = session.query(PendingProject).filter_by(uuid=request.uuid).first()
            if pending_project is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'not found pending project uuid: {request.uuid}')
            participants_map = pending_project.get_participants_info().participants_map
            peer_info = pending_project.get_participant_info(peer_pure_domain)
            if not peer_info or peer_info.role == ProjectRole.PARTICIPANT.name:
                context.abort(grpc.StatusCode.PERMISSION_DENIED,
                              f'{peer_pure_domain} is not coordinator in pending project {request.uuid}')
            if _is_same_participants(participants_map, request.participants_map):
                context.abort(grpc.StatusCode.PERMISSION_DENIED,
                              f'can not change participants when the pending project {request.uuid} has been approved')
            participants_map.MergeFrom(request.participants_map)
            pending_project.set_participants_info(ParticipantsInfo(participants_map=participants_map))
            session.commit()
        return empty_pb2.Empty()

    @emits_rpc_event(resource_type=Event.ResourceType.PENDING_PROJECT,
                     op_type=Event.OperationType.CONTROL_STATE,
                     resource_name_fn=lambda request: request.uuid)
    def SyncPendingProjectState(self, request: SyncPendingProjectStateRequest, context: ServicerContext):
        peer_pure_domain = get_pure_domain_from_context(context)
        if request.state not in [PendingProjectState.ACCEPTED.name, PendingProjectState.CLOSED.name]:
            context.abort(grpc.StatusCode.PERMISSION_DENIED,
                          f'participant can only sync ACCEPTED or CLOSED but got: {request.state}')
        with db.session_scope() as session:
            session.connection(execution_options={'isolation_level': 'SERIALIZABLE'})
            pending_project: PendingProject = session.query(PendingProject).filter_by(uuid=request.uuid).first()
            if pending_project is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'not found pending project uuid: {request.uuid}')
            participants_info = pending_project.get_participants_info()
            if peer_pure_domain not in participants_info.participants_map:
                context.abort(grpc.StatusCode.PERMISSION_DENIED,
                              f'{peer_pure_domain} is not in pending project {request.uuid}')
            participants_info.participants_map[peer_pure_domain].state = request.state
            pending_project.set_participants_info(participants_info)
            session.commit()
        return empty_pb2.Empty()

    @emits_rpc_event(resource_type=Event.ResourceType.PROJECT,
                     op_type=Event.OperationType.CREATE,
                     resource_name_fn=lambda request: request.uuid)
    def CreateProject(self, request: CreateProjectRequest, context: ServicerContext):
        with db.session_scope() as session:
            pending_project: PendingProject = session.query(PendingProject).filter_by(uuid=request.uuid).first()

            if pending_project is None:
                message = f'failed to find pending project, uuid is {request.uuid}'
                logging.error(message)
                context.abort(grpc.StatusCode.NOT_FOUND, message)

            if pending_project.state == PendingProjectState.CLOSED:
                logging.info(f'{pending_project.uuid} pending project has closed')
                return empty_pb2.Empty()

            if pending_project.state != PendingProjectState.ACCEPTED:
                message = f'{pending_project.uuid} pending project has not been accepted'
                logging.info(message)
                context.abort(grpc.StatusCode.FAILED_PRECONDITION, message)

            project = session.query(Project).filter_by(name=pending_project.name).first()
            if project is not None:
                message = f'{pending_project.name} project has already existed, uuid is {pending_project.uuid}'
                logging.error(message)
                context.abort(grpc.StatusCode.ALREADY_EXISTS, message)

        with db.session_scope() as session:
            session.connection(execution_options={'isolation_level': 'SERIALIZABLE'})
            PendingProjectService(session).create_project_locally(pending_project.uuid)
            session.commit()
        return empty_pb2.Empty()

    @emits_rpc_event(resource_type=Event.ResourceType.PROJECT,
                     op_type=Event.OperationType.DELETE,
                     resource_name_fn=lambda request: request.uuid)
    def DeletePendingProject(self, request: CreateProjectRequest, context: ServicerContext):
        peer_pure_domain = get_pure_domain_from_context(context)
        with db.session_scope() as session:
            pending_project: PendingProject = session.query(PendingProject).filter_by(uuid=request.uuid).first()
            if pending_project is None:
                return empty_pb2.Empty()
            if peer_pure_domain != pending_project.get_coordinator_info()[0]:
                context.abort(grpc.StatusCode.PERMISSION_DENIED,
                              f'{peer_pure_domain} is not coordinator in pending project {request.uuid}')
            pending_project.deleted_at = now()
            session.commit()
        return empty_pb2.Empty()

    def SendTemplateRevision(self, request: SendTemplateRevisionRequest, context: ServicerContext):
        peer_pure_domain = get_pure_domain_from_context(context)
        with db.session_scope() as session:
            WorkflowTemplateRevisionService(session).create_revision(
                name=request.name,
                kind=request.kind,
                config=request.config,
                revision_index=request.revision_index,
                comment=request.comment,
                peer_pure_domain=peer_pure_domain,
            )
            session.commit()
            return empty_pb2.Empty()

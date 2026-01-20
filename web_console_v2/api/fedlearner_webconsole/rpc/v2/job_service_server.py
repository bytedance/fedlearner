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
import grpc
from grpc import ServicerContext
from google.protobuf import empty_pb2
import sqlalchemy
from fedlearner_webconsole.dataset.auth_service import AuthService
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.rpc.v2 import job_service_pb2_grpc
from fedlearner_webconsole.proto.rpc.v2.job_service_pb2 import CreateModelJobRequest, InformTrustedJobGroupRequest, \
    UpdateTrustedJobGroupRequest, DeleteTrustedJobGroupRequest, GetTrustedJobGroupRequest, \
    GetTrustedJobGroupResponse, CreateDatasetJobStageRequest, GetDatasetJobStageRequest, GetDatasetJobStageResponse, \
    CreateModelJobGroupRequest, GetModelJobGroupRequest, GetModelJobRequest, InformModelJobGroupRequest, \
    InformTrustedJobRequest, GetTrustedJobRequest, GetTrustedJobResponse, CreateTrustedExportJobRequest, \
    UpdateDatasetJobSchedulerStateRequest, UpdateModelJobGroupRequest, InformModelJobRequest
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobPb, ModelJobGroupPb
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.tee.services import TrustedJobGroupService, TrustedJobService
from fedlearner_webconsole.tee.models import TrustedJobGroup, TrustedJob, TrustedJobStatus, TrustedJobType
from fedlearner_webconsole.mmgr.models import ModelJobRole, ModelJobType, AlgorithmType, ModelJobGroup, ModelJob, \
    GroupCreateStatus, GroupAutoUpdateStatus
from fedlearner_webconsole.mmgr.service import ModelJobService, ModelJobGroupService
from fedlearner_webconsole.rpc.v2.utils import get_grpc_context_info
from fedlearner_webconsole.dataset.job_configer.dataset_job_configer import DatasetJobConfiger
from fedlearner_webconsole.dataset.models import DatasetJob, DatasetJobSchedulerState, DatasetJobStage, Dataset
from fedlearner_webconsole.dataset.services import DatasetService
from fedlearner_webconsole.dataset.local_controllers import DatasetJobStageLocalController
from fedlearner_webconsole.dataset.services import DatasetJobService
from fedlearner_webconsole.utils.pp_datetime import from_timestamp
from fedlearner_webconsole.utils.proto import remove_secrets
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.algorithm.fetcher import AlgorithmFetcher
from fedlearner_webconsole.exceptions import NotFoundException
from fedlearner_webconsole.audit.decorators import emits_rpc_event
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.review.ticket_helper import get_ticket_helper


class JobServiceServicer(job_service_pb2_grpc.JobServiceServicer):

    @emits_rpc_event(resource_type=Event.ResourceType.TRUSTED_JOB_GROUP,
                     op_type=Event.OperationType.INFORM,
                     resource_name_fn=lambda request: request.uuid)
    def InformTrustedJobGroup(self, request: InformTrustedJobGroupRequest, context: ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project_id, client_id = get_grpc_context_info(session, context)
            group: TrustedJobGroup = session.query(TrustedJobGroup).populate_existing().with_for_update().filter_by(
                project_id=project_id, uuid=request.uuid).first()
            if group is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'trusted job group {request.uuid} not found')
            try:
                auth_status = AuthStatus[request.auth_status]
            except KeyError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f'auth_status {request.auth_status} is invalid')
            unauth_set = set(group.get_unauth_participant_ids())
            if auth_status == AuthStatus.AUTHORIZED:
                unauth_set.discard(client_id)
            else:
                unauth_set.add(client_id)
            group.set_unauth_participant_ids(list(unauth_set))
            session.commit()
        return empty_pb2.Empty()

    @emits_rpc_event(resource_type=Event.ResourceType.TRUSTED_JOB_GROUP,
                     op_type=Event.OperationType.UPDATE,
                     resource_name_fn=lambda request: request.uuid)
    def UpdateTrustedJobGroup(self, request: UpdateTrustedJobGroupRequest, context: ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project_id, client_id = get_grpc_context_info(session, context)
            group: TrustedJobGroup = session.query(TrustedJobGroup).filter_by(project_id=project_id,
                                                                              uuid=request.uuid).first()
            if group is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'trusted job group {request.uuid} not found')
            if client_id != group.coordinator_id:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, 'only coordinator can update algorithm')
            try:
                algorithm = AlgorithmFetcher(project_id).get_algorithm(request.algorithm_uuid)
                old_algorithm = AlgorithmFetcher(project_id).get_algorithm(group.algorithm_uuid)
                if algorithm.algorithm_project_uuid != old_algorithm.algorithm_project_uuid:
                    context.abort(grpc.StatusCode.INVALID_ARGUMENT, 'upstream algorithm project mismatch')
            except NotFoundException as e:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, e.message)
            group.algorithm_uuid = request.algorithm_uuid
            session.commit()
        return empty_pb2.Empty()

    @emits_rpc_event(resource_type=Event.ResourceType.TRUSTED_JOB_GROUP,
                     op_type=Event.OperationType.DELETE,
                     resource_name_fn=lambda request: request.uuid)
    def DeleteTrustedJobGroup(self, request: DeleteTrustedJobGroupRequest, context: ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project_id, client_id = get_grpc_context_info(session, context)
            group: TrustedJobGroup = session.query(TrustedJobGroup).filter_by(project_id=project_id,
                                                                              uuid=request.uuid).first()
            if group is None:
                return empty_pb2.Empty()
            if client_id != group.coordinator_id:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, 'only coordinator can delete the trusted job group')
            if not group.is_deletable():
                context.abort(grpc.StatusCode.FAILED_PRECONDITION, 'trusted job is not deletable')
            TrustedJobGroupService(session).delete(group)
            session.commit()
        return empty_pb2.Empty()

    def GetTrustedJobGroup(self, request: GetTrustedJobGroupRequest,
                           context: ServicerContext) -> GetTrustedJobGroupResponse:
        with db.session_scope() as session:
            project_id, _ = get_grpc_context_info(session, context)
            group: TrustedJobGroup = session.query(TrustedJobGroup).filter_by(project_id=project_id,
                                                                              uuid=request.uuid).first()
            if group is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'trusted job group {request.uuid} not found')
            return GetTrustedJobGroupResponse(auth_status=group.auth_status.name)

    def GetModelJob(self, request: GetModelJobRequest, context: ServicerContext) -> ModelJobPb:
        with db.session_scope() as session:
            project_id, _ = get_grpc_context_info(session, context)
            model_job: ModelJob = session.query(ModelJob).filter_by(uuid=request.uuid).first()
            if model_job is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'model job with uuid {request.uuid} is not found')
            return remove_secrets(model_job.to_proto())

    @emits_rpc_event(resource_type=Event.ResourceType.MODEL_JOB,
                     op_type=Event.OperationType.CREATE,
                     resource_name_fn=lambda request: request.uuid)
    def CreateModelJob(self, request: CreateModelJobRequest, context: ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project_id, client_id = get_grpc_context_info(session, context)
            if session.query(ModelJob).filter_by(uuid=request.uuid).first() is not None:
                return empty_pb2.Empty()
            if session.query(ModelJob).filter_by(name=request.name).first() is not None:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f'model job {request.name} already exist')
            group = session.query(ModelJobGroup).filter_by(uuid=request.group_uuid).first()
            if group is None:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f'model job group {request.group_uuid} not found')
            model_job_type = ModelJobType[request.model_job_type]
            if model_job_type in [ModelJobType.TRAINING] and group.latest_version >= request.version:
                context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT, f'the latest version of model group {group.name} '
                    f'is larger than or equal to the given version')
            service = ModelJobService(session)
            algorithm_type = AlgorithmType[request.algorithm_type]
            data_batch_id = None
            dataset_job_stage_uuid = request.global_config.dataset_job_stage_uuid
            if dataset_job_stage_uuid != '':
                dataset_job_stage = session.query(DatasetJobStage).filter_by(uuid=dataset_job_stage_uuid).first()
                data_batch_id = dataset_job_stage.data_batch_id
            model_job = service.create_model_job(name=request.name,
                                                 uuid=request.uuid,
                                                 group_id=group.id,
                                                 project_id=project_id,
                                                 role=ModelJobRole.PARTICIPANT,
                                                 model_job_type=model_job_type,
                                                 algorithm_type=algorithm_type,
                                                 coordinator_id=client_id,
                                                 data_batch_id=data_batch_id,
                                                 global_config=request.global_config,
                                                 version=request.version)
            if model_job_type in [ModelJobType.TRAINING]:
                group.latest_version = model_job.version
            session.commit()
        return empty_pb2.Empty()

    @emits_rpc_event(resource_type=Event.ResourceType.MODEL_JOB,
                     op_type=Event.OperationType.INFORM,
                     resource_name_fn=lambda request: request.uuid)
    def InformModelJob(self, request: InformModelJobRequest, context: ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project_id, client_id = get_grpc_context_info(session, context)
            model_job: ModelJob = session.query(ModelJob).populate_existing().with_for_update().filter_by(
                project_id=project_id, uuid=request.uuid).first()
            if model_job is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'model job {request.uuid} is not found')
            try:
                auth_status = AuthStatus[request.auth_status]
            except KeyError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f'auth_status {request.auth_status} is invalid')
            pure_domain_name = session.query(Participant).get(client_id).pure_domain_name()
            participants_info = model_job.get_participants_info()
            participants_info.participants_map[pure_domain_name].auth_status = auth_status.name
            model_job.set_participants_info(participants_info)
            session.commit()
            return empty_pb2.Empty()

    @emits_rpc_event(resource_type=Event.ResourceType.DATASET_JOB_STAGE,
                     op_type=Event.OperationType.CREATE,
                     resource_name_fn=lambda request: request.dataset_job_uuid)
    def CreateDatasetJobStage(self, request: CreateDatasetJobStageRequest, context: ServicerContext) -> empty_pb2.Empty:
        try:
            with db.session_scope() as session:
                # we set isolation_level to SERIALIZABLE to make sure state won't be changed within this session
                session.connection(execution_options={'isolation_level': 'SERIALIZABLE'})
                _, client_id = get_grpc_context_info(session, context)
                dataset_job: DatasetJob = session.query(DatasetJob).filter(
                    DatasetJob.uuid == request.dataset_job_uuid).first()
                if dataset_job is None:
                    context.abort(grpc.StatusCode.INVALID_ARGUMENT,
                                  f'dataset_job {request.dataset_job_uuid} is not found')
                if dataset_job.output_dataset is None:
                    context.abort(grpc.StatusCode.INVALID_ARGUMENT,
                                  f'output dataset is not found, dataset_job uuid: {request.dataset_job_uuid}')
                # check authorization
                if not AuthService(session=session, dataset_job=dataset_job).check_local_authorized():
                    message = '[CreateDatasetJobStage] still waiting for authorized, ' \
                        f'dataset_job_uuid: {request.dataset_job_uuid}'
                    logging.warning(message)
                    context.abort(grpc.StatusCode.PERMISSION_DENIED, message)
                event_time = from_timestamp(request.event_time) if request.event_time else None
                # check data_batch ready
                data_batch = DatasetService(session).get_data_batch(dataset=dataset_job.input_dataset,
                                                                    event_time=event_time)
                if data_batch is None or not data_batch.is_available():
                    message = '[CreateDatasetJobStage] input_dataset data_batch is not ready, ' \
                        f'datasetJob uuid: {request.dataset_job_uuid}'
                    logging.warning(message)
                    context.abort(grpc.StatusCode.FAILED_PRECONDITION, message)
                DatasetJobStageLocalController(session=session).create_data_batch_and_job_stage_as_participant(
                    dataset_job_id=dataset_job.id,
                    coordinator_id=client_id,
                    uuid=request.dataset_job_stage_uuid,
                    name=request.name,
                    event_time=event_time)
                session.commit()
        except sqlalchemy.exc.OperationalError as e:
            # catch deadlock exception
            logging.warning('[create dataset job stage rpc]: [SKIP] catch operation error in session', exc_info=True)
        return empty_pb2.Empty()

    def GetDatasetJobStage(self, request: GetDatasetJobStageRequest,
                           context: ServicerContext) -> GetDatasetJobStageResponse:
        with db.session_scope() as session:
            dataset_job_stage: DatasetJobStage = session.query(DatasetJobStage).filter(
                DatasetJobStage.uuid == request.dataset_job_stage_uuid).first()
            if dataset_job_stage is None:
                context.abort(code=grpc.StatusCode.NOT_FOUND,
                              details=f'could not find dataset_job_stage {request.dataset_job_stage_uuid}')
            dataset_job_stage_proto = dataset_job_stage.to_proto()
            dataset_job_stage_proto.workflow_definition.MergeFrom(
                DatasetJobConfiger.from_kind(dataset_job_stage.dataset_job.kind, session).get_config())
            return GetDatasetJobStageResponse(dataset_job_stage=dataset_job_stage_proto)

    def UpdateDatasetJobSchedulerState(self, request: UpdateDatasetJobSchedulerStateRequest,
                                       context: ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project_id, _ = get_grpc_context_info(session, context)
            dataset_job: DatasetJob = session.query(DatasetJob).filter(DatasetJob.project_id == project_id).filter(
                DatasetJob.uuid == request.uuid).first()
            if dataset_job is None:
                context.abort(code=grpc.StatusCode.NOT_FOUND, details=f'could not find dataset_job {request.uuid}')
            if request.scheduler_state == DatasetJobSchedulerState.RUNNABLE.name:
                DatasetJobService(session=session).start_cron_scheduler(dataset_job=dataset_job)
            elif request.scheduler_state == DatasetJobSchedulerState.STOPPED.name:
                DatasetJobService(session=session).stop_cron_scheduler(dataset_job=dataset_job)
            else:
                context.abort(code=grpc.StatusCode.INVALID_ARGUMENT,
                              details='scheduler state must in [RUNNABLE, STOPPED]')
            session.commit()
        return empty_pb2.Empty()

    def GetModelJobGroup(self, request: GetModelJobGroupRequest, context: ServicerContext) -> ModelJobGroupPb:
        with db.session_scope() as session:
            project_id, _ = get_grpc_context_info(session, context)
            group = session.query(ModelJobGroup).filter_by(uuid=request.uuid).first()
            if group is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'model job group with uuid {request.uuid} is not found')
            return remove_secrets(group.to_proto())

    @emits_rpc_event(resource_type=Event.ResourceType.MODEL_JOB_GROUP,
                     op_type=Event.OperationType.INFORM,
                     resource_name_fn=lambda request: request.uuid)
    def InformModelJobGroup(self, request: InformModelJobGroupRequest, context: ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project_id, client_id = get_grpc_context_info(session, context)
            group: ModelJobGroup = session.query(ModelJobGroup).populate_existing().with_for_update().filter_by(
                project_id=project_id, uuid=request.uuid).first()
            if group is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'model job group {request.uuid} is not found')
            try:
                auth_status = AuthStatus[request.auth_status]
            except KeyError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f'auth_status {request.auth_status} is invalid')
            pure_domain_name = session.query(Participant).get(client_id).pure_domain_name()
            participants_info = group.get_participants_info()
            participants_info.participants_map[pure_domain_name].auth_status = auth_status.name
            group.set_participants_info(participants_info)
            session.commit()
            return empty_pb2.Empty()

    def UpdateModelJobGroup(self, request: UpdateModelJobGroupRequest, context: ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project_id, _ = get_grpc_context_info(session, context)
            group: ModelJobGroup = session.query(ModelJobGroup).populate_existing().with_for_update().filter_by(
                project_id=project_id, uuid=request.uuid).first()
            if group is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'model job group {request.uuid} is not found')
            if request.auto_update_status != '':
                try:
                    auto_update_status = GroupAutoUpdateStatus[request.auto_update_status]
                except KeyError:
                    context.abort(grpc.StatusCode.INVALID_ARGUMENT,
                                  f'auto_update_status {request.auto_update_status} is invalid')
                group.auto_update_status = auto_update_status
            if request.start_dataset_job_stage_uuid != '':
                dataset_job_stage = session.query(DatasetJobStage).filter_by(
                    uuid=request.start_dataset_job_stage_uuid).first()
                group.start_data_batch_id = dataset_job_stage.data_batch_id
            session.commit()
            return empty_pb2.Empty()

    @emits_rpc_event(resource_type=Event.ResourceType.MODEL_JOB_GROUP,
                     op_type=Event.OperationType.INFORM,
                     resource_name_fn=lambda request: request.uuid)
    def CreateModelJobGroup(self, request: CreateModelJobGroupRequest, context: ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project_id, client_id = get_grpc_context_info(session, context)
            group = session.query(ModelJobGroup).filter_by(uuid=request.uuid).first()
            if group is not None:
                return empty_pb2.Empty()
            dataset = session.query(Dataset).filter_by(uuid=request.dataset_uuid).first()
            if dataset is None:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f'dataset with uuid {request.uuid} is not found')
            service = ModelJobGroupService(session)
            algorithm_type = AlgorithmType[request.algorithm_type]
            group = service.create_group(name=request.name,
                                         uuid=request.uuid,
                                         project_id=project_id,
                                         role=ModelJobRole.PARTICIPANT,
                                         dataset_id=dataset.id,
                                         algorithm_type=algorithm_type,
                                         algorithm_project_list=request.algorithm_project_list,
                                         coordinator_id=client_id)
            group.status = GroupCreateStatus.SUCCEEDED
            session.add(group)
            session.commit()
        return empty_pb2.Empty()

    def InformTrustedJob(self, request: InformTrustedJobRequest, context: ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project_id, client_id = get_grpc_context_info(session, context)
            trusted_job: TrustedJob = session.query(TrustedJob).filter_by(project_id=project_id,
                                                                          uuid=request.uuid).first()
            if trusted_job is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'trusted job {request.uuid} not found')
            try:
                auth_status = AuthStatus[request.auth_status]
            except KeyError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f'auth_status {request.auth_status} is invalid')
            pure_domain_name = session.query(Participant).get(client_id).pure_domain_name()
            participants_info = trusted_job.get_participants_info()
            participants_info.participants_map[pure_domain_name].auth_status = auth_status.name
            trusted_job.set_participants_info(participants_info)
            session.commit()
        return empty_pb2.Empty()

    def GetTrustedJob(self, request: GetTrustedJobRequest, context: ServicerContext) -> GetTrustedJobResponse:
        with db.session_scope() as session:
            project_id, _ = get_grpc_context_info(session, context)
            trusted_job: TrustedJob = session.query(TrustedJob).filter_by(project_id=project_id,
                                                                          uuid=request.uuid).first()
            if trusted_job is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'trusted job {request.uuid} not found')
            return GetTrustedJobResponse(auth_status=trusted_job.auth_status.name)

    def CreateTrustedExportJob(self, request: CreateTrustedExportJobRequest,
                               context: ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project_id, client_id = get_grpc_context_info(session, context)
            validate = get_ticket_helper(session).validate_ticket(request.ticket_uuid,
                                                                  lambda ticket: ticket.details.uuid == request.uuid)
            if not validate:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, f'ticket {request.ticket_uuid} is not validated')
            tee_analyze_job = session.query(TrustedJob).filter_by(project_id=project_id,
                                                                  type=TrustedJobType.ANALYZE,
                                                                  uuid=request.parent_uuid).first()
            if tee_analyze_job is None or tee_analyze_job.get_status() != TrustedJobStatus.SUCCEEDED:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f'tee_analyze_job {request.parent_uuid} invalid')
            TrustedJobService(session).create_external_export(request.uuid, request.name, client_id,
                                                              request.export_count, request.ticket_uuid,
                                                              tee_analyze_job)
            session.commit()
        return empty_pb2.Empty()

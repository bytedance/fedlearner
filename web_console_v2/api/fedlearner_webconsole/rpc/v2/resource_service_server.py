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

import grpc
from grpc import ServicerContext
from google.protobuf import empty_pb2
from typing import Iterable
from datetime import timedelta

from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.proto import remove_secrets
from fedlearner_webconsole.proto.rpc.v2 import resource_service_pb2_grpc
from fedlearner_webconsole.proto.rpc.v2.resource_service_pb2 import GetAlgorithmRequest, GetAlgorithmProjectRequest, \
    InformDatasetRequest, ListAlgorithmProjectsRequest, ListAlgorithmProjectsResponse, ListAlgorithmsRequest, \
    ListAlgorithmsResponse, GetAlgorithmFilesRequest, GetAlgorithmFilesResponse, ListDatasetsRequest, \
    ListDatasetsResponse
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmProjectPb, AlgorithmPb
from fedlearner_webconsole.algorithm.service import AlgorithmProjectService, AlgorithmService
from fedlearner_webconsole.algorithm.models import AlgorithmProject, Algorithm, PublishStatus
from fedlearner_webconsole.algorithm.transmit.sender import AlgorithmSender
from fedlearner_webconsole.dataset.models import Dataset, DatasetKindV2, ResourceState
from fedlearner_webconsole.dataset.services import DatasetService
from fedlearner_webconsole.dataset.auth_service import AuthService
from fedlearner_webconsole.rpc.v2.utils import get_grpc_context_info, get_pure_domain_from_context
from fedlearner_webconsole.audit.decorators import emits_rpc_event
from fedlearner_webconsole.proto.audit_pb2 import Event


class ResourceServiceServicer(resource_service_pb2_grpc.ResourceServiceServicer):

    def ListAlgorithmProjects(self, request: ListAlgorithmProjectsRequest,
                              context: ServicerContext) -> ListAlgorithmProjectsResponse:
        with db.session_scope() as session:
            project_id, _ = get_grpc_context_info(session, context)
            algo_projects = AlgorithmProjectService(session).get_published_algorithm_projects(
                project_id=project_id, filter_exp=request.filter_exp)
            algorithm_projects = []
            for algo_project in algo_projects:
                algo_project.updated_at = AlgorithmProjectService(session).get_published_algorithms_latest_update_time(
                    algo_project.id)
                algorithm_projects.append(remove_secrets(algo_project.to_proto()))
        return ListAlgorithmProjectsResponse(algorithm_projects=algorithm_projects)

    def ListAlgorithms(self, request: ListAlgorithmsRequest, context: ServicerContext) -> ListAlgorithmsResponse:
        with db.session_scope() as session:
            project_id, _ = get_grpc_context_info(session, context)
            algorithm_project: AlgorithmProject = session.query(AlgorithmProject). \
                filter_by(project_id=project_id,
                          uuid=request.algorithm_project_uuid).first()
            if algorithm_project is None:
                context.abort(grpc.StatusCode.NOT_FOUND,
                              f'algorithm_project uuid: {request.algorithm_project_uuid} not found')
            algos = AlgorithmService(session).get_published_algorithms(project_id=project_id,
                                                                       algorithm_project_id=algorithm_project.id)
            algorithms = []
            for algo in algos:
                algorithms.append(remove_secrets(algo.to_proto()))
        return ListAlgorithmsResponse(algorithms=algorithms)

    def GetAlgorithmProject(self, request: GetAlgorithmProjectRequest, context: ServicerContext) -> AlgorithmProjectPb:
        with db.session_scope() as session:
            algo_project: AlgorithmProject = session.query(AlgorithmProject).filter_by(
                uuid=request.algorithm_project_uuid).first()
            if algo_project is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'algorithm project uuid:'
                              f' {request.algorithm_project_uuid} not found')
            if algo_project.publish_status != PublishStatus.PUBLISHED:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, f'algorithm project uuid:'
                              f' {request.algorithm_project_uuid} is not published')
            return remove_secrets(algo_project.to_proto())

    def GetAlgorithm(self, request: GetAlgorithmRequest, context: ServicerContext) -> AlgorithmPb:
        with db.session_scope() as session:
            algorithm: Algorithm = session.query(Algorithm).filter_by(uuid=request.algorithm_uuid).first()
            if algorithm is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'algorithm uuid: {request.algorithm_uuid} not found')
            if algorithm.publish_status != PublishStatus.PUBLISHED:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, f'algorithm uuid: {request.algorithm_uuid} '
                              f'is not published')
            return remove_secrets(algorithm.to_proto())

    def GetAlgorithmFiles(self, request: GetAlgorithmFilesRequest,
                          context: ServicerContext) -> Iterable[GetAlgorithmFilesResponse]:
        with db.session_scope() as session:
            algorithm: Algorithm = session.query(Algorithm).filter_by(uuid=request.algorithm_uuid).first()
            if algorithm is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'algorithm uuid: {request.algorithm_uuid} not found')
            if algorithm.publish_status != PublishStatus.PUBLISHED:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, f'algorithm uuid: {request.algorithm_uuid} '
                              f'is not published')
        yield from AlgorithmSender().make_algorithm_iterator(algorithm.path)

    @emits_rpc_event(resource_type=Event.ResourceType.DATASET,
                     op_type=Event.OperationType.INFORM,
                     resource_name_fn=lambda request: request.uuid)
    def InformDataset(self, request: InformDatasetRequest, context: ServicerContext) -> empty_pb2.Empty:
        with db.session_scope() as session:
            project_id, _ = get_grpc_context_info(session, context)
            participant_pure_domain = get_pure_domain_from_context(context)
            dataset: Dataset = session.query(Dataset).populate_existing().with_for_update().filter_by(
                project_id=project_id, uuid=request.uuid).first()
            if dataset is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f'dataset {request.uuid} not found')
            try:
                AuthStatus[request.auth_status]
            except KeyError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f'auth_status {request.auth_status} is invalid')

            participants_info = dataset.get_participants_info()
            if participant_pure_domain not in participants_info.participants_map:
                context.abort(grpc.StatusCode.PERMISSION_DENIED,
                              f'{participant_pure_domain} is not participant of dataset {request.uuid}')
            AuthService(session=session, dataset_job=dataset.parent_dataset_job).update_auth_status(
                domain_name=participant_pure_domain, auth_status=AuthStatus[request.auth_status])
            session.commit()
        return empty_pb2.Empty()

    def ListDatasets(self, request: ListDatasetsRequest, context: ServicerContext) -> ListDatasetsResponse:
        kind = DatasetKindV2[request.kind] if request.kind else None
        uuid = request.uuid if request.uuid else None
        state = ResourceState[request.state] if request.state else None
        time_range = timedelta(days=request.time_range.days, hours=request.time_range.hours)
        # set time_range to None if time_range is empty
        if not time_range:
            time_range = None
        with db.session_scope() as session:
            project_id, _ = get_grpc_context_info(session, context)
            datasets = DatasetService(session=session).get_published_datasets(project_id=project_id,
                                                                              kind=kind,
                                                                              uuid=uuid,
                                                                              state=state,
                                                                              time_range=time_range)
            return ListDatasetsResponse(participant_datasets=datasets)

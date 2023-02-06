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
import logging
from google.protobuf import json_format
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import Dataset, DataBatch
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.mmgr.models import Model, ModelJob, ModelJobGroup, ModelJobType, GroupCreateStatus, \
    GroupAutoUpdateStatus
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.algorithm.fetcher import AlgorithmFetcher
from fedlearner_webconsole.mmgr.service import check_model_job_group, ModelJobGroupService
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.two_pc.transaction_manager import TransactionManager
from fedlearner_webconsole.proto.two_pc_pb2 import TwoPcType, TransactionData, CreateModelJobData, \
    CreateModelJobGroupData
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobGroupPb
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.rpc.v2.job_service_client import JobServiceClient
from fedlearner_webconsole.rpc.v2.system_service_client import SystemServiceClient
from fedlearner_webconsole.workflow.workflow_job_controller import start_workflow, stop_workflow
from fedlearner_webconsole.workflow_template.utils import set_value
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.exceptions import InternalException
from fedlearner_webconsole.flag.models import Flag


def _get_transaction_manager(project_id: int, two_pc_type: TwoPcType) -> TransactionManager:
    with db.session_scope() as session:
        project = session.query(Project).get(project_id)
        participants = ParticipantService(session).get_platform_participants_by_project(project_id)
        tm = TransactionManager(project_name=project.name,
                                project_token=project.token,
                                two_pc_type=two_pc_type,
                                participants=[participant.domain_name for participant in participants])
        return tm


class CreateModelJob:

    @staticmethod
    def _create_model_job_by_2pc(project_id: int,
                                 name: str,
                                 model_job_type: ModelJobType,
                                 algorithm_type: AlgorithmType,
                                 coordinator_pure_domain_name: str,
                                 dataset_id: Optional[int] = None,
                                 model_id: Optional[int] = None,
                                 group_id: Optional[int] = None) -> Tuple[bool, str]:
        tm = _get_transaction_manager(project_id=project_id, two_pc_type=TwoPcType.CREATE_MODEL_JOB)
        with db.session_scope() as session:
            project_name = session.query(Project).get(project_id).name
            dataset_uuid = None
            if dataset_id is not None:
                dataset_uuid = session.query(Dataset).get(dataset_id).uuid
            model_uuid = None
            if model_id is not None:
                model_uuid = session.query(Model).get(model_id).uuid
            group_name = None
            if group_id is not None:
                group_name = session.query(ModelJobGroup).get(group_id).name
        model_job_uuid = resource_uuid()
        workflow_uuid = model_job_uuid
        succeeded, message = tm.run(
            TransactionData(
                create_model_job_data=CreateModelJobData(model_job_name=name,
                                                         model_job_uuid=model_job_uuid,
                                                         model_job_type=model_job_type.name,
                                                         group_name=group_name,
                                                         algorithm_type=algorithm_type.name,
                                                         workflow_uuid=workflow_uuid,
                                                         model_uuid=model_uuid,
                                                         project_name=project_name,
                                                         coordinator_pure_domain_name=coordinator_pure_domain_name,
                                                         dataset_uuid=dataset_uuid)))
        return succeeded, message

    def run(self,
            project_id: int,
            name: str,
            model_job_type: ModelJobType,
            algorithm_type: AlgorithmType,
            coordinator_pure_domain_name: str,
            dataset_id: Optional[int],
            model_id: Optional[int] = None,
            group_id: Optional[int] = None) -> Tuple[bool, str]:
        # no need create model job at participants when eval or predict horizontal model
        if algorithm_type in [AlgorithmType.TREE_VERTICAL, AlgorithmType.NN_VERTICAL
                             ] or model_job_type == ModelJobType.TRAINING:
            succeeded, msg = self._create_model_job_by_2pc(project_id=project_id,
                                                           name=name,
                                                           model_job_type=model_job_type,
                                                           algorithm_type=algorithm_type,
                                                           coordinator_pure_domain_name=coordinator_pure_domain_name,
                                                           dataset_id=dataset_id,
                                                           model_id=model_id,
                                                           group_id=group_id)
            return succeeded, msg
        with db.session_scope() as session:
            model_job = ModelJob(name=name,
                                 group_id=group_id,
                                 project_id=project_id,
                                 model_job_type=model_job_type,
                                 algorithm_type=algorithm_type,
                                 model_id=model_id)
            model_job.uuid = resource_uuid()
            model_job.workflow_uuid = model_job.uuid
            session.add(model_job)
            session.commit()
            return True, ''


class CreateModelJobGroup:

    @staticmethod
    def run(project_id: int, name: str, algorithm_type: AlgorithmType, dataset_id: Optional[str],
            coordinator_pure_domain_name: str, model_job_group_uuid: str) -> Tuple[bool, str]:
        with db.session_scope() as session:
            project_name = session.query(Project).get(project_id).name
            dataset_uuid = None
            if dataset_id is not None:
                dataset_uuid = session.query(Dataset).get(dataset_id).uuid
        tm = _get_transaction_manager(project_id=project_id, two_pc_type=TwoPcType.CREATE_MODEL_JOB_GROUP)
        create_model_job_group_data = CreateModelJobGroupData(model_job_group_name=name,
                                                              model_job_group_uuid=model_job_group_uuid,
                                                              project_name=project_name,
                                                              algorithm_type=algorithm_type.name,
                                                              coordinator_pure_domain_name=coordinator_pure_domain_name,
                                                              dataset_uuid=dataset_uuid)
        succeeded, msg = tm.run(data=TransactionData(create_model_job_group_data=create_model_job_group_data))
        return succeeded, msg


class LaunchModelJob:

    @staticmethod
    def run(project_id: int, group_id: int, version: int):
        tm = _get_transaction_manager(project_id=project_id, two_pc_type=TwoPcType.LAUNCH_MODEL_JOB)
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(group_id)
            model_job_name = f'{group.name}-v{group.latest_version}'
        data = TransactionData(create_model_job_data=CreateModelJobData(
            model_job_name=model_job_name, model_job_uuid=resource_uuid(), group_uuid=group.uuid, version=version))
        succeeded, msg = tm.run(data)
        return succeeded, msg


class ModelJobGroupController:

    def __init__(self, session: Session, project_id: int):
        self._session = session
        self._clients = []
        self._participants = ParticipantService(self._session).get_participants_by_project(project_id)
        self._project = self._session.query(Project).get(project_id)
        for p in self._participants:
            self._clients.append(JobServiceClient.from_project_and_participant(p.domain_name, self._project.name))

    def inform_auth_status_to_participants(self, group: ModelJobGroup):
        participants_info = group.get_participants_info()
        pure_domain_name = SettingService.get_system_info().pure_domain_name
        participants_info.participants_map[pure_domain_name].auth_status = group.auth_status.name
        group.set_participants_info(participants_info)
        for client, p in zip(self._clients, self._participants):
            try:
                client.inform_model_job_group(group.uuid, group.auth_status)
            except grpc.RpcError as e:
                logging.warning(f'[model-job-group] failed to inform participant {p.id}\'s '
                                f'model job group {group.uuid} with grpc code {e.code()} and details {e.details()}')

    def update_participants_model_job_group(self,
                                            uuid: str,
                                            auto_update_status: Optional[GroupAutoUpdateStatus] = None,
                                            start_data_batch_id: Optional[int] = None):
        start_dataset_job_stage_uuid = None
        if start_data_batch_id:
            start_dataset_job_stage_uuid = self._session.query(DataBatch).get(
                start_data_batch_id).latest_parent_dataset_job_stage.uuid
        for client, p in zip(self._clients, self._participants):
            try:
                client.update_model_job_group(uuid=uuid,
                                              auto_update_status=auto_update_status,
                                              start_dataset_job_stage_uuid=start_dataset_job_stage_uuid)
            except grpc.RpcError as e:
                logging.warning(f'[model-job-group] failed to update participant {p.id}\'s '
                                f'model job group {uuid} with grpc code {e.code()} and details {e.details()}')

    def update_participants_auth_status(self, group: ModelJobGroup):
        participants_info = group.get_participants_info()
        for client, p in zip(self._clients, self._participants):
            try:
                resp = client.get_model_job_group(group.uuid)
                if resp.auth_status:
                    auth_status = resp.auth_status
                else:
                    # Use 'authorized' if the field 'auth_status' is not in the ModelJobGroupPb of the opposite side
                    if resp.authorized:
                        auth_status = AuthStatus.AUTHORIZED.name
                    else:
                        auth_status = AuthStatus.PENDING.name
                participants_info.participants_map[p.pure_domain_name()].auth_status = auth_status
            except grpc.RpcError as e:
                logging.warning(f'[model-job-group] failed to get participant {p.id}\'s '
                                f'model job group {group.uuid} with grpc code {e.code()} and details {e.details()}')
        group.set_participants_info(participants_info)
        self._session.commit()

    def get_model_job_group_from_participant(self, participant_id: int,
                                             model_job_group_uuid: str) -> Optional[ModelJobGroupPb]:
        resp = None
        for client, p in zip(self._clients, self._participants):
            if p.id == participant_id:
                try:
                    resp = client.get_model_job_group(uuid=model_job_group_uuid)
                    system_client = SystemServiceClient.from_participant(domain_name=p.domain_name)
                    flag_resp = system_client.list_flags()
                    break
                except grpc.RpcError as e:
                    logging.warning(
                        f'[model-job-group] failed to get participant {p.id}\'s '
                        f'model job group {model_job_group_uuid} with grpc code {e.code()} and details {e.details()}')
        if resp and len(resp.config.job_definitions) and flag_resp.get(Flag.MODEL_JOB_GLOBAL_CONFIG_ENABLED.name):
            variables = resp.config.job_definitions[0].variables
            for variable in variables:
                if variable.name == 'algorithm':
                    algo_dict = json_format.MessageToDict(variable.typed_value)
                    algo = AlgorithmFetcher(self._project.id).get_algorithm(algo_dict['algorithmUuid'])
                    algo_dict['algorithmId'] = algo.id
                    algo_dict['participantId'] = algo.participant_id
                    algo_dict['algorithmProjectId'] = algo.algorithm_project_id
                    set_value(variable=variable, typed_value=algo_dict)
                    break
        return resp

    def create_model_job_group_for_participants(self, model_job_group_id: int):
        group = self._session.query(ModelJobGroup).get(model_job_group_id)
        for client, p in zip(self._clients, self._participants):
            try:
                client.create_model_job_group(name=group.name,
                                              uuid=group.uuid,
                                              algorithm_type=group.algorithm_type,
                                              dataset_uuid=group.dataset.uuid,
                                              algorithm_project_list=group.get_algorithm_project_uuid_list())
            except grpc.RpcError as e:
                logging.warning(f'[model-job-group] failed to create model job group for the participant {p.id} '
                                f'with grpc code {e.code()} and details {e.details()}')
                group.status = GroupCreateStatus.FAILED
                return
        group.status = GroupCreateStatus.SUCCEEDED


class ModelJobController:

    def __init__(self, session: Session, project_id: int):
        self._session = session
        self._client = []
        self._participants = ParticipantService(self._session).get_participants_by_project(project_id)
        self._project_id = project_id
        project = self._session.query(Project).get(project_id)
        for p in self._participants:
            self._client.append(JobServiceClient.from_project_and_participant(p.domain_name, project.name))

    def launch_model_job(self, group_id: int) -> ModelJob:
        check_model_job_group(self._project_id, group_id, self._session)
        group = ModelJobGroupService(self._session).lock_and_update_version(group_id)
        self._session.commit()
        succeeded, msg = LaunchModelJob().run(project_id=self._project_id,
                                              group_id=group_id,
                                              version=group.latest_version)
        if not succeeded:
            raise InternalException(f'launching model job by 2PC with message: {msg}')
        model_job = self._session.query(ModelJob).filter_by(group_id=group_id, version=group.latest_version).first()
        return model_job

    def inform_auth_status_to_participants(self, model_job: ModelJob):
        for client, p in zip(self._client, self._participants):
            try:
                client.inform_model_job(model_job.uuid, model_job.auth_status)
            except grpc.RpcError as e:
                logging.warning(f'[model-job] failed to inform participants {p.id}\'s model job '
                                f'{model_job.uuid} with grpc code {e.code()} and details {e.details()}')

    def update_participants_auth_status(self, model_job: ModelJob):
        participants_info = model_job.get_participants_info()
        for client, p in zip(self._client, self._participants):
            try:
                resp = client.get_model_job(model_job.uuid)
                participants_info.participants_map[p.pure_domain_name()].auth_status = resp.auth_status
            except grpc.RpcError as e:
                logging.warning(f'[model-job] failed to get participant {p.id}\'s model job {model_job.uuid} '
                                f'with grpc code {e.code()} and details {e.details()}')
        model_job.set_participants_info(participants_info)


# TODO(gezhengqiang): provide start model job rpc
def start_model_job(model_job_id: int):
    with db.session_scope() as session:
        model_job: ModelJob = session.query(ModelJob).get(model_job_id)
        start_workflow(workflow_id=model_job.workflow_id)


def stop_model_job(model_job_id: int):
    with db.session_scope() as session:
        model_job: ModelJob = session.query(ModelJob).get(model_job_id)
        stop_workflow(workflow_id=model_job.workflow_id)

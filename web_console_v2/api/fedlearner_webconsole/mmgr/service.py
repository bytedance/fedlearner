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
from typing import Optional
from sqlalchemy.orm import Session

from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.exceptions import InvalidArgumentException, NotFoundException
from fedlearner_webconsole.mmgr.metrics.metrics_inquirer import tree_metrics_inquirer, nn_metrics_inquirer
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, ModelTrainingCronJobInput
from fedlearner_webconsole.proto.metrics_pb2 import ModelJobMetrics
from fedlearner_webconsole.job.metrics import JobMetricsBuilder
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.algorithm.models import AlgorithmType, Algorithm, AlgorithmProject, Source
from fedlearner_webconsole.mmgr.models import Model, ModelJob, ModelType, ModelJobGroup, ModelJobType, ModelJobRole, \
    ModelJobStatus, AuthStatus
from fedlearner_webconsole.mmgr.utils import deleted_name
from fedlearner_webconsole.mmgr.model_job_configer import get_sys_template_id, ModelJobConfiger
from fedlearner_webconsole.mmgr.utils import get_job_path, build_workflow_name, \
    is_model_job
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobKind, DataBatch
from fedlearner_webconsole.composer.composer_service import CronJobService
from fedlearner_webconsole.workflow.workflow_controller import create_ready_workflow
from fedlearner_webconsole.workflow.service import CreateNewWorkflowParams, WorkflowService
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.utils.pp_datetime import now
from fedlearner_webconsole.utils.const import SYSTEM_WORKFLOW_CREATOR_USERNAME
from fedlearner_webconsole.utils.base_model import auth_model
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobGlobalConfig, ModelJobConfig, AlgorithmProjectList
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.rpc.v2.job_service_client import JobServiceClient


def get_project(project_id: int, session: Session) -> Project:
    project = session.query(Project).get(project_id)
    if project is None:
        raise NotFoundException(f'project {project_id} is not found')
    return project


def get_dataset(dataset_id: int, session: Session) -> Dataset:
    dataset = session.query(Dataset).get(dataset_id)
    if dataset is None:
        raise InvalidArgumentException(f'dataset {dataset_id} is not found')
    return dataset


def get_model_job(project_id: int, model_job_id: int, session: Session) -> ModelJob:
    model_job = session.query(ModelJob).filter_by(id=model_job_id, project_id=project_id).first()
    if model_job is None:
        raise NotFoundException(f'[Model]model job {model_job_id} is not found')
    return model_job


def get_model_job_group(project_id: int, group_id: int, session: Session) -> ModelJobGroup:
    query = session.query(ModelJobGroup).filter_by(id=group_id, project_id=project_id)
    group = query.first()
    if group is None:
        raise NotFoundException(f'[Model]model group {group_id} is not found')
    return group


def check_model_job_group(project_id: int, group_id: int, sesseion: Session):
    group = sesseion.query(ModelJobGroup).filter_by(id=group_id, project_id=project_id).first()
    if group is None:
        raise NotFoundException(f'[Model]model group {group_id} is not found')


def get_participant(participant_id: int, project: Project) -> Participant:
    for participant in project.participants:
        if participant.id == participant_id:
            return participant
    raise NotFoundException(f'participant {participant_id} is not found')


def get_model(project_id: int, model_id: int, session: Session) -> Model:
    model = session.query(Model).filter_by(project_id=project_id, id=model_id).first()
    if model is None:
        raise NotFoundException(f'[Model]model {model_id} is not found')
    return model


def get_algorithm(project_id: int, algorithm_id: int, session: Session) -> Optional[Algorithm]:
    query = session.query(Algorithm)
    if project_id:
        # query under project and preset algorithms with project_id as null
        query = query.filter((Algorithm.project_id == project_id) | (Algorithm.source == Source.PRESET))
    algo = query.filter_by(id=algorithm_id).first()
    return algo


class ModelJobService:

    def __init__(self, session):
        self._session = session

    @staticmethod
    def query_metrics(model_job: ModelJob, job: Optional[Job] = None) -> ModelJobMetrics:
        job = job or model_job.job
        builder = JobMetricsBuilder(job)
        if model_job.algorithm_type == AlgorithmType.TREE_VERTICAL:
            model_job_metrics = tree_metrics_inquirer.query(job, need_feature_importance=True)
            if len(model_job_metrics.train) == 0 and len(model_job_metrics.eval) == 0:
                # legacy metrics support
                logging.info(f'use legacy tree model metrics, job name = {job.name}')
                return builder.query_tree_metrics(need_feature_importance=True)
            return model_job_metrics
        if model_job.algorithm_type == AlgorithmType.NN_VERTICAL:
            model_job_metrics = nn_metrics_inquirer.query(job)
            if len(model_job_metrics.train) == 0 and len(model_job_metrics.eval) == 0:
                # legacy metrics support
                logging.info(f'use legacy nn model metrics, job name = {job.name}')
                return builder.query_nn_metrics()
            return model_job_metrics
        if model_job.algorithm_type == AlgorithmType.NN_HORIZONTAL:
            return builder.query_nn_metrics()
        raise ValueError(f'invalid algorithm type {model_job.algorithm_type}')

    @staticmethod
    def _get_job(workflow: Workflow) -> Optional[Job]:
        for job in workflow.owned_jobs:
            if is_model_job(job.job_type):
                return job
        return None

    def _create_model_job_for_participants(self, model_job: ModelJob):
        project = self._session.query(Project).get(model_job.project_id)
        group = self._session.query(ModelJobGroup).get(model_job.group_id)
        global_config = model_job.get_global_config()
        for participant in project.participants:
            client = JobServiceClient.from_project_and_participant(participant.domain_name, project.name)
            try:
                client.create_model_job(name=model_job.name,
                                        uuid=model_job.uuid,
                                        group_uuid=group.uuid,
                                        model_job_type=model_job.model_job_type,
                                        algorithm_type=model_job.algorithm_type,
                                        global_config=global_config,
                                        version=model_job.version)
                logging.info(f'[ModelJob] model job {model_job.id} is ready')
            except Exception as e:  # pylint: disable=broad-except
                logging.exception('[ModelJob] creating model job for participants failed')
                raise Exception(f'[ModelJob] creating model job for participants failed with detail {str(e)}') from e

    # TODO(hangweiqiang): ensure version is unique for training job under model job group
    def create_model_job(self,
                         name: str,
                         uuid: str,
                         project_id: int,
                         role: ModelJobRole,
                         model_job_type: ModelJobType,
                         algorithm_type: AlgorithmType,
                         global_config: ModelJobGlobalConfig,
                         group_id: Optional[int] = None,
                         coordinator_id: Optional[int] = 0,
                         data_batch_id: Optional[int] = None,
                         version: Optional[int] = None,
                         comment: Optional[str] = None) -> ModelJob:
        model_job = ModelJob(name=name,
                             uuid=uuid,
                             group_id=group_id,
                             project_id=project_id,
                             role=role,
                             model_job_type=model_job_type,
                             algorithm_type=algorithm_type,
                             coordinator_id=coordinator_id,
                             version=version,
                             comment=comment)
        assert global_config.dataset_uuid != '', 'dataset uuid must not be empty'
        dataset = self._session.query(Dataset).filter_by(uuid=global_config.dataset_uuid).first()
        assert dataset is not None, f'dataset with uuid {global_config.dataset_uuid} is not found'
        model_job.dataset_id = dataset.id
        if data_batch_id is not None:  # for auto update jobs
            assert algorithm_type in [AlgorithmType.NN_VERTICAL],\
                'auto update is only supported for nn vertical train'
            dataset_job: DatasetJob = self._session.query(DatasetJob).filter_by(output_dataset_id=dataset.id).first()
            assert dataset_job.kind != DatasetJobKind.RSA_PSI_DATA_JOIN,\
                'auto update is not supported for RSA-PSI dataset'
            data_batch: DataBatch = self._session.query(DataBatch).get(data_batch_id)
            assert data_batch is not None, f'data batch {data_batch_id} is not found'
            assert data_batch.is_available(), f'data batch {data_batch_id} is not available'
            assert data_batch.latest_parent_dataset_job_stage is not None, 'dataset job stage with id is not found'
            model_job.data_batch_id = data_batch_id
            model_job.auto_update = True
            if role in [ModelJobRole.COORDINATOR]:
                global_config.dataset_job_stage_uuid = data_batch.latest_parent_dataset_job_stage.uuid
        model_job.set_global_config(global_config)
        self.initialize_auth_status(model_job)
        # when model job type is eval or predict
        if global_config.model_uuid != '':
            model = self._session.query(Model).filter_by(uuid=global_config.model_uuid).first()
            assert model is not None, f'model with uuid {global_config.model_uuid} is not found'
            model_job.model_id = model.id
            # add model's group id to model_job when eval and predict
            model_job.group_id = model.group_id
        pure_domain_name = SettingService(session=self._session).get_system_info().pure_domain_name
        model_job_config: ModelJobConfig = global_config.global_config.get(pure_domain_name)
        assert model_job_config is not None, f'model_job_config of self domain name {pure_domain_name} must not be None'
        if model_job_config.algorithm_uuid != '':
            algorithm = self._session.query(Algorithm).filter_by(uuid=model_job_config.algorithm_uuid).first()
            # algorithm is none if algorithm_uuid points to a published algorithm at the peer platform
            if algorithm is not None:
                model_job.algorithm_id = algorithm.id
        # no need create model job at participants when eval or predict horizontal model
        if model_job_type in [ModelJobType.TRAINING] and role in [ModelJobRole.COORDINATOR]:
            self._create_model_job_for_participants(model_job)
        if model_job_type in [ModelJobType.EVALUATION, ModelJobType.PREDICTION] and algorithm_type not in [
                AlgorithmType.NN_HORIZONTAL
        ] and role in [ModelJobRole.COORDINATOR]:
            self._create_model_job_for_participants(model_job)
        self._session.add(model_job)
        return model_job

    def config_model_job(self,
                         model_job: ModelJob,
                         config: WorkflowDefinition,
                         create_workflow: bool,
                         need_to_create_ready_workflow: Optional[bool] = False,
                         workflow_uuid: Optional[str] = None):
        workflow_name = build_workflow_name(model_job_type=model_job.model_job_type.name,
                                            algorithm_type=model_job.algorithm_type.name,
                                            model_job_name=model_job.name)
        template_id = get_sys_template_id(self._session, model_job.algorithm_type, model_job.model_job_type)
        if template_id is None:
            raise ValueError(f'workflow template for {model_job.algorithm_type.name} not found')
        workflow_comment = f'created by model_job {model_job.name}'
        configer = ModelJobConfiger(session=self._session,
                                    model_job_type=model_job.model_job_type,
                                    algorithm_type=model_job.algorithm_type,
                                    project_id=model_job.project_id)
        configer.set_dataset(config=config, dataset_id=model_job.dataset_id, data_batch_id=model_job.data_batch_id)
        if need_to_create_ready_workflow:
            workflow = create_ready_workflow(
                session=self._session,
                name=workflow_name,
                config=config,
                project_id=model_job.project_id,
                template_id=template_id,
                uuid=workflow_uuid,
                comment=workflow_comment,
            )
        elif create_workflow:
            params = CreateNewWorkflowParams(project_id=model_job.project_id, template_id=template_id)
            workflow = WorkflowService(self._session).create_workflow(name=workflow_name,
                                                                      config=config,
                                                                      params=params,
                                                                      comment=workflow_comment,
                                                                      uuid=workflow_uuid,
                                                                      creator_username=SYSTEM_WORKFLOW_CREATOR_USERNAME)
        else:
            workflow = self._session.query(Workflow).filter_by(uuid=model_job.workflow_uuid).first()
            if workflow is None:
                raise ValueError(f'workflow with uuid {model_job.workflow_uuid} not found')
            workflow = WorkflowService(self._session).config_workflow(workflow=workflow,
                                                                      template_id=template_id,
                                                                      config=config,
                                                                      comment=workflow_comment,
                                                                      creator_username=SYSTEM_WORKFLOW_CREATOR_USERNAME)
        self._session.flush()
        model_job.workflow_id = workflow.id
        model_job.workflow_uuid = workflow.uuid
        job = self._get_job(workflow)
        assert job is not None, 'model job not found in workflow'
        model_job.job_name = job.name
        model_job.job_id = job.id
        model_job.status = ModelJobStatus.CONFIGURED
        self._session.flush()

    def update_model_job_status(self, model_job: ModelJob):
        workflow = self._session.query(Workflow).filter_by(uuid=model_job.workflow_uuid).first()
        if workflow:
            if workflow.state in [WorkflowState.RUNNING]:
                model_job.status = ModelJobStatus.RUNNING
            if workflow.state in [WorkflowState.STOPPED]:
                model_job.status = ModelJobStatus.STOPPED
            if workflow.state in [WorkflowState.COMPLETED]:
                model_job.status = ModelJobStatus.SUCCEEDED
            if workflow.state in [WorkflowState.FAILED]:
                model_job.status = ModelJobStatus.FAILED

    def initialize_auth_status(self, model_job: ModelJob):
        pure_domain_name = SettingService(self._session).get_system_info().pure_domain_name
        participants = ParticipantService(self._session).get_participants_by_project(model_job.project_id)
        # 1. default all authorized when model job type is training
        # 2. default all authorized when algorithm type is nn_horizontal and model job type is evaluation or prediction
        # 3. set coordinator authorized when algorithm type is not nn_horizontal and model job type is evaluation or
        #    prediction
        participants_info = ParticipantsInfo(participants_map={
            p.pure_domain_name(): ParticipantInfo(auth_status=AuthStatus.PENDING.name) for p in participants
        })
        participants_info.participants_map[pure_domain_name].auth_status = AuthStatus.PENDING.name
        if model_job.model_job_type in [ModelJobType.TRAINING
                                       ] or model_job.algorithm_type in [AlgorithmType.NN_HORIZONTAL]:
            participants_info = ParticipantsInfo(participants_map={
                p.pure_domain_name(): ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name) for p in participants
            })
            participants_info.participants_map[pure_domain_name].auth_status = AuthStatus.AUTHORIZED.name
            model_job.auth_status = AuthStatus.AUTHORIZED
        elif model_job.role in [ModelJobRole.COORDINATOR]:
            participants_info.participants_map[pure_domain_name].auth_status = AuthStatus.AUTHORIZED.name
            model_job.auth_status = AuthStatus.AUTHORIZED
        model_job.set_participants_info(participants_info)

    @staticmethod
    def update_model_job_auth_status(model_job: ModelJob, auth_status: AuthStatus):
        model_job.auth_status = auth_status
        participants_info = model_job.get_participants_info()
        pure_domain_name = SettingService.get_system_info().pure_domain_name
        participants_info.participants_map[pure_domain_name].auth_status = auth_status.name
        model_job.set_participants_info(participants_info)

    def delete(self, job_id: int):
        model_job: ModelJob = self._session.query(ModelJob).get(job_id)
        model_job.deleted_at = now()
        model_job.name = deleted_name(model_job.name)
        if model_job.output_model is not None:
            ModelService(self._session).delete(model_job.output_model.id)


class ModelService:

    def __init__(self, session: Session):
        self._session = session

    def create_model_from_model_job(self, model_job: ModelJob):
        name = f'{model_job.group.name}-v{model_job.version}'
        model_type = ModelType.NN_MODEL
        if model_job.algorithm_type == AlgorithmType.TREE_VERTICAL:
            model_type = ModelType.TREE_MODEL
        model = Model(name=name,
                      uuid=model_job.uuid,
                      version=model_job.version,
                      model_type=model_type,
                      algorithm_type=model_job.algorithm_type,
                      project_id=model_job.project_id,
                      job_id=model_job.job_id,
                      group_id=model_job.group_id,
                      model_job_id=model_job.id)
        storage_root_dir = model_job.project.get_storage_root_path(None)
        if storage_root_dir is None:
            logging.warning(f'[ModelService] storage root of project {model_job.project.name} is None')
            raise RuntimeError(f'storage root of project {model_job.project.name} is None')
        model.model_path = get_job_path(storage_root_dir, model_job.job.name)
        self._session.add(model)

    def delete(self, model_id: int):
        model: Model = self._session.query(Model).get(model_id)
        model.deleted_at = now()
        model.name = deleted_name(model.name)


class ModelJobGroupService:

    def __init__(self, session: Session):
        self._session = session

    def launch_model_job(self, group: ModelJobGroup, name: str, uuid: str, version: int) -> ModelJob:
        model_job = ModelJob(
            name=name,
            uuid=uuid,
            group_id=group.id,
            project_id=group.project_id,
            model_job_type=ModelJobType.TRAINING,
            algorithm_type=group.algorithm_type,
            algorithm_id=group.algorithm_id,
            dataset_id=group.dataset_id,
            version=version,
        )
        self._session.add(model_job)
        self._session.flush()
        ModelJobService(self._session).config_model_job(model_job,
                                                        group.get_config(),
                                                        create_workflow=False,
                                                        need_to_create_ready_workflow=True,
                                                        workflow_uuid=model_job.uuid)
        group.latest_version = version
        self._session.flush()
        return model_job

    def delete(self, group_id: int):
        group: ModelJobGroup = self._session.query(ModelJobGroup).get(group_id)
        group.name = deleted_name(group.name)
        group.deleted_at = now()
        job_service = ModelJobService(self._session)
        for job in group.model_jobs:
            job_service.delete(job.id)

    def lock_and_update_version(self, group_id: int) -> ModelJobGroup:
        group: ModelJobGroup = self._session.query(ModelJobGroup).populate_existing().with_for_update().get(group_id)
        # use exclusive lock to ensure version is unique and increasing.
        # since 2PC has its own db transaction, and the latest_version of group should be updated in service,
        # to avoid lock conflict, the latest_version is updated and lock is released,
        # and the version is passed to 2PC transaction.
        group.latest_version = group.latest_version + 1
        return group

    def update_cronjob_config(self, group: ModelJobGroup, cron_config: str):
        """Update model training cron job config

        Args:
            group: group for updating cron config
            cron_config: cancel cron job if cron config is empty string; create
                or update cron job if cron config is valid
        """
        item_name = f'model_training_cron_job_{group.id}'
        group.cron_config = cron_config
        if cron_config:
            runner_input = RunnerInput(model_training_cron_job_input=ModelTrainingCronJobInput(group_id=group.id))
            items = [(ItemType.MODEL_TRAINING_CRON_JOB, runner_input)]
            CronJobService(self._session).start_cronjob(item_name=item_name, items=items, cron_config=cron_config)
        else:
            CronJobService(self._session).stop_cronjob(item_name=item_name)

    def create_group(self, name: str, uuid: str, project_id: int, role: ModelJobRole, dataset_id: int,
                     algorithm_type: AlgorithmType, algorithm_project_list: AlgorithmProjectList,
                     coordinator_id: int) -> ModelJobGroup:
        dataset = self._session.query(Dataset).get(dataset_id)
        assert dataset is not None, f'dataset with id {dataset_id} is not found'
        group = ModelJobGroup(name=name,
                              uuid=uuid,
                              role=role,
                              project_id=project_id,
                              dataset_id=dataset_id,
                              algorithm_type=algorithm_type,
                              coordinator_id=coordinator_id)
        group.set_algorithm_project_uuid_list(algorithm_project_list)
        pure_domain_name = SettingService(session=self._session).get_system_info().pure_domain_name
        algorithm_project_uuid = algorithm_project_list.algorithm_projects.get(pure_domain_name)
        if algorithm_project_uuid is None and algorithm_type != AlgorithmType.TREE_VERTICAL:
            raise Exception(f'algorithm project uuid must be given if algorithm type is {algorithm_type.name}')
        if algorithm_project_uuid is not None:
            algorithm_project = self._session.query(AlgorithmProject).filter_by(uuid=algorithm_project_uuid).first()
            # algorithm project is none if uuid points to a published algorithm at the peer platform
            if algorithm_project is not None:
                group.algorithm_project_id = algorithm_project.id
        self._session.add(group)
        return group

    def get_latest_model_from_model_group(self, model_group_id: int) -> Model:
        model = self._session.query(Model).filter_by(group_id=model_group_id).order_by(Model.version.desc()).first()
        if model is None:
            raise InvalidArgumentException(f'model in group {model_group_id} is not found')
        return model

    def initialize_auth_status(self, group: ModelJobGroup):
        # set auth status map
        pure_domain_name = SettingService(self._session).get_system_info().pure_domain_name
        participants = ParticipantService(self._session).get_participants_by_project(group.project_id)
        participants_info = ParticipantsInfo(participants_map={
            p.pure_domain_name(): ParticipantInfo(auth_status=AuthStatus.PENDING.name) for p in participants
        })
        participants_info.participants_map[pure_domain_name].auth_status = AuthStatus.AUTHORIZED.name
        group.set_participants_info(participants_info)
        # compatible with older versions of auth status
        group.authorized = True
        group.auth_status = auth_model.AuthStatus.AUTHORIZED

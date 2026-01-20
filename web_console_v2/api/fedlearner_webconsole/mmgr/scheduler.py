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
from sqlalchemy import or_
from typing import List, Tuple

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.services import BatchService
from fedlearner_webconsole.composer.interface import IRunnerV2, RunnerContext, RunnerOutput
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.mmgr.models import ModelJob, ModelJobRole, ModelJobStatus, ModelJobGroup, \
    GroupCreateStatus, GroupAutoUpdateStatus, Model, ModelJobType, ModelJobAuthFrontendStatus
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobConfig
from fedlearner_webconsole.mmgr.model_job_configer import ModelJobConfiger, set_load_model_name
from fedlearner_webconsole.mmgr.service import ModelJobService, ModelJobGroupService
from fedlearner_webconsole.mmgr.controller import ModelJobGroupController
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.resource_name import resource_uuid


class ModelJobSchedulerRunner(IRunnerV2):

    @staticmethod
    def _check_model_job(model_job_id: int):
        """check workflow state and update model job status"""
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(model_job_id)
            ModelJobService(session).update_model_job_status(model_job)
            session.commit()
            logging.info(f'[ModelJobScheduler] model_job {model_job.name} updates status to {model_job.status}')

    @staticmethod
    def _config_model_job(model_job_id: int):
        """config model job by calling model job configer and model job service"""
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).get(model_job_id)
            global_config = model_job.get_global_config()
            if global_config is None:
                ModelJobService(session).update_model_job_status(model_job)
                session.commit()
                return
            domain_name = SettingService(session).get_system_info().pure_domain_name
            model_job_config: ModelJobConfig = global_config.global_config.get(domain_name)
            try:
                configer = ModelJobConfiger(session=session,
                                            model_job_type=model_job.model_job_type,
                                            algorithm_type=model_job.algorithm_type,
                                            project_id=model_job.project_id)
                config = configer.get_config(dataset_id=model_job.dataset_id,
                                             model_id=model_job.model_id,
                                             model_job_config=model_job_config)
                ModelJobService(session).config_model_job(model_job=model_job,
                                                          config=config,
                                                          create_workflow=False,
                                                          need_to_create_ready_workflow=True,
                                                          workflow_uuid=model_job.uuid)
            except Exception as e:  # pylint: disable=broad-except
                logging.exception(f'[ModelJobScheduler] config model job {model_job_id} failed')
                model_job.error_message = str(e)
                model_job.status = ModelJobStatus.ERROR
            finally:
                session.commit()
        logging.info(f'[ModelJobScheduler] model_job {model_job_id} is CONFIGURED')

    def schedule_model_job(self):
        # 1. filter training model job with status PENDING and evaluation or prediction model job with status PENDING
        #    and ModelJobAuthFrontendStatus ALL_AUTHORIZED, and pull algorithm and create workflow, then status
        #    becomes CONFIGURED
        with db.session_scope() as session:
            training_model_job_ids: List[Tuple[int]] = session.query(ModelJob.id).filter_by(
                status=ModelJobStatus.PENDING, model_job_type=ModelJobType.TRAINING).all()
            non_training_model_job_ids: List[Tuple[int]] = session.query(
                ModelJob.id).filter(ModelJob.model_job_type != ModelJobType.TRAINING).filter(
                    ModelJob.status == ModelJobStatus.PENDING).all()
        for training_model_job_id, *_ in training_model_job_ids:
            self._config_model_job(model_job_id=training_model_job_id)
        for non_training_model_job_id, *_ in non_training_model_job_ids:
            with db.session_scope() as session:
                model_job = session.query(ModelJob).get(non_training_model_job_id)
                if model_job.get_model_job_auth_frontend_status() in [ModelJobAuthFrontendStatus.ALL_AUTHORIZED]:
                    self._config_model_job(model_job_id=non_training_model_job_id)
        # 2. filter model job with status CONFIGURED, RUNNING, and update the model job status
        model_job_ids: List[Tuple[int]] = session.query(ModelJob.id).filter(
            or_(ModelJob.status == ModelJobStatus.CONFIGURED, ModelJob.status == ModelJobStatus.RUNNING)).all()
        for model_job_id, *_ in model_job_ids:
            self._check_model_job(model_job_id=model_job_id)

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        try:
            self.schedule_model_job()
        except Exception as e:  # pylint: disable=broad-except
            logging.exception('[ModelJobScheduler] schedule model job failed')
            return RunnerStatus.FAILED, RunnerOutput(error_message=str(e))

        return RunnerStatus.DONE, RunnerOutput()


class ModelJobGroupSchedulerRunner(IRunnerV2):

    @staticmethod
    def _create_model_job_group_for_participants(model_job_group_id: int):
        """create model job group for the participants"""
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(model_job_group_id)
            ModelJobGroupController(session=session,
                                    project_id=group.project_id).create_model_job_group_for_participants(
                                        model_job_group_id=model_job_group_id)
            session.commit()

    def _schedule_model_job_group(self):
        # filter model job group with ticket status APPROVED, create the model job group for the participants
        with db.session_scope() as session:
            model_job_group_ids: List[Tuple[int]] = session.query(
                ModelJobGroup.id).filter_by(role=ModelJobRole.COORDINATOR,
                                            status=GroupCreateStatus.PENDING,
                                            ticket_status=TicketStatus.APPROVED).all()
        for model_job_group_id, *_ in model_job_group_ids:
            self._create_model_job_group_for_participants(model_job_group_id=model_job_group_id)

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        try:
            self._schedule_model_job_group()
        except Exception as e:  # pylint: disable=broad-except
            logging.exception('[ModelJobGroupScheduler] schedule model job group failed')
            return RunnerStatus.FAILED, RunnerOutput(error_message=str(e))

        return RunnerStatus.DONE, RunnerOutput()


class ModelJobGroupLongPeriodScheduler(IRunnerV2):

    @staticmethod
    def _create_auto_update_model_job(model_job_group_id: int):
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(auto_update=True, group_id=model_job_group_id).order_by(
                ModelJob.created_at.desc()).limit(1).first()
            if model_job is None:
                group = session.query(ModelJobGroup).get(model_job_group_id)
                logging.warning(f'There is no auto update model jobs in the model job group {group.name}')
                return
            if model_job.status not in [ModelJobStatus.SUCCEEDED]:
                logging.warning(f'The status of the latest auto update model job {model_job.name} is not SUCCEEDED')
                return
            next_data_batch = BatchService(session).get_next_batch(model_job.data_batch)
            if next_data_batch is None:
                logging.warning(
                    f'There is no next data batch after the data batch with name: {model_job.data_batch.name}')
                return
            group: ModelJobGroup = ModelJobGroupService(session).lock_and_update_version(model_job_group_id)
            version = group.latest_version
            model_job_name = f'{group.name}-v{version}'
            # Load the model of the previous model job for the new training job
            model_name = model_job.model_name()
            if model_name is None:
                model = session.query(Model).filter_by(name=model_job.name).first()
                if model is None:
                    raise Exception(f'model_job {model_job.name}\'s model is not found')
                model_job.model_id = model.id
                model_name = model.name
            global_config = model_job.get_global_config()
            if global_config is not None:
                for config in global_config.global_config.values():
                    set_load_model_name(config, model_name)
            ModelJobService(session).create_model_job(name=model_job_name,
                                                      uuid=resource_uuid(),
                                                      role=ModelJobRole.COORDINATOR,
                                                      model_job_type=model_job.model_job_type,
                                                      algorithm_type=model_job.algorithm_type,
                                                      global_config=global_config,
                                                      group_id=model_job_group_id,
                                                      project_id=model_job.project_id,
                                                      data_batch_id=next_data_batch.id,
                                                      comment=model_job.comment,
                                                      version=version)
            session.commit()

    def _schedule_model_job_group(self):
        # filter model job group with auto update status ACTIVE,
        # create auto update model job for all participants by COORDINATOR
        with db.session_scope() as session:
            model_job_group_ids: List[Tuple[int]] = session.query(ModelJobGroup.id).filter_by(
                role=ModelJobRole.COORDINATOR, auto_update_status=GroupAutoUpdateStatus.ACTIVE).all()
        for model_job_group_id, *_ in model_job_group_ids:
            try:
                self._create_auto_update_model_job(model_job_group_id=model_job_group_id)
            except Exception as e:  # pylint: disable=broad-except
                logging.exception(f'[ModelJobGroupLongPeriodScheduler] fail to create auto update model job for '
                                  f'group id: {model_job_group_id}')

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        self._schedule_model_job_group()
        return RunnerStatus.DONE, RunnerOutput()

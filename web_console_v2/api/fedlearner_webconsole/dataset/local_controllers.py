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

from datetime import datetime
import logging
from typing import Optional
from sqlalchemy.orm import Session

from fedlearner_webconsole.dataset.models import DataBatch, DatasetJob, DatasetJobStage, DatasetJobState, \
    DatasetType
from fedlearner_webconsole.dataset.services import BatchService, DatasetJobStageService, DatasetService
from fedlearner_webconsole.proto.dataset_pb2 import BatchParameter, DatasetJobGlobalConfigs, CronType
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.workflow.workflow_controller import start_workflow_locally, stop_workflow_locally


class DatasetJobStageLocalController(object):

    def __init__(self, session: Session):
        self._session = session
        self._dataset_job_stage_service = DatasetJobStageService(session)

    def start(self, dataset_job_stage: DatasetJobStage):
        """start dataset job stage task locally

        1. start related workflow locally
        2. set dataset job stage's state to RUNNING
        """
        start_workflow_locally(self._session, dataset_job_stage.workflow)
        self._dataset_job_stage_service.start_dataset_job_stage(dataset_job_stage=dataset_job_stage)
        logging.info('[dataset_job_stage_local_controller]: start successfully')

    def stop(self, dataset_job_stage: DatasetJobStage):
        """stop dataset job stage task locally

        1. stop related workflow locally
        2. set dataset job stage's state to STOPPED
        """
        if dataset_job_stage.workflow is not None:
            stop_workflow_locally(self._session, dataset_job_stage.workflow)
        else:
            logging.info(f'workflow not found, just skip! workflow id: {dataset_job_stage.workflow_id}')
        self._dataset_job_stage_service.finish_dataset_job_stage(dataset_job_stage=dataset_job_stage,
                                                                 finish_state=DatasetJobState.STOPPED)
        logging.info('[dataset_job_stage_local_controller]: stop successfully')

    # TODO(liuhehan): delete in the near future after we use as_coordinator func
    def create_data_batch_and_job_stage(self,
                                        dataset_job_id: int,
                                        event_time: Optional[datetime] = None,
                                        uuid: Optional[str] = None,
                                        name: Optional[str] = None) -> Optional[DatasetJobStage]:
        """create data_batch and job_stage locally

        UseCase 1: create new data_batch and new job_stage with given uuid and name:
            only called as role of participants, uuid and name are given by coordinator
            will create both data_batch and job_stage

            Parameters:
                dataset_job_id(int): dataset_job id
                event_time(datetime): optional; only works in STREAMING dataset_job,
                    event_time of current data_batch and job_stage
                uuid(str): uuid of dataset_job_stage
                name(str): name of dataset_job_stage

            Returns:
                dataset_job_stage(DatasetJobStage): dataset_job_stage which created in func

        UseCase 2: create new data_batch and new job_stage for PSI/STREAMING dataset_job:
            only called as role of coordinator
            will create both data_batch and job_stage

            Parameters:
                dataset_job_id(int): dataset_job id
                event_time(datetime): optional; only works in STREAMING dataset_job,
                    event_time of current data_batch and job_stage

            Returns:
                dataset_job_stage(DatasetJobStage): dataset_job_stage which created in func

        UseCase 3: rerun data_batch:
            called to create a new job_stage when data_batch failed
            will create only dataset_job_stage if find target data_batch

            Parameters:
                dataset_job_id(int): dataset_job id
                event_time(datetime): optional; only works in STREAMING dataset_job,
                    event_time of current data_batch and job_stage

            Returns:
                dataset_job_stage(DatasetJobStage): dataset_job_stage which created in func
        """
        dataset_job: DatasetJob = self._session.query(DatasetJob).get(dataset_job_id)
        if dataset_job.output_dataset.dataset_type == DatasetType.STREAMING:
            data_batch = self._session.query(DataBatch).filter(
                DataBatch.dataset_id == dataset_job.output_dataset_id).filter(
                    DataBatch.event_time == event_time).first()
        else:
            data_batch = self._session.query(DataBatch).filter(
                DataBatch.dataset_id == dataset_job.output_dataset_id).first()
        # create data_batch if not exist:
        if data_batch is None:
            batch_parameter = BatchParameter(dataset_id=dataset_job.output_dataset_id)
            if event_time:
                batch_parameter.event_time = to_timestamp(event_time)
            data_batch = BatchService(self._session).create_batch(batch_parameter=batch_parameter)
            self._session.flush()
        dataset_job_stage = None
        if uuid:
            dataset_job_stage = self._session.query(DatasetJobStage).filter(DatasetJobStage.uuid == uuid).first()
        # for idempotent, skip if dataset_job_stage exists:
        if dataset_job_stage is None:
            dataset_job_stage = self._dataset_job_stage_service.create_dataset_job_stage(
                project_id=dataset_job.project_id,
                dataset_job_id=dataset_job_id,
                output_data_batch_id=data_batch.id,
                uuid=uuid,
                name=name)
        return dataset_job_stage

    def create_data_batch_and_job_stage_as_coordinator(
            self,
            dataset_job_id: int,
            global_configs: DatasetJobGlobalConfigs,
            event_time: Optional[datetime] = None) -> Optional[DatasetJobStage]:
        """create data_batch and job_stage locally as coordinator

        UseCase 1: create new data_batch and new job_stage for PSI/STREAMING dataset:
            only called as role of coordinator
            will create both data_batch and job_stage

            Parameters:
                dataset_job_id(int): dataset_job id
                global_configs(global_configs): configs of all participants for this dataset_job_stage
                event_time(datetime): optional; only works in STREAMING dataset,
                    event_time of current data_batch and job_stage

            Returns:
                dataset_job_stage(DatasetJobStage): dataset_job_stage which created in func

        UseCase 2: rerun data_batch:
            called to create a new job_stage when data_batch failed,
            will create only dataset_job_stage if find target data_batch

            Parameters:
                dataset_job_id(int): dataset_job id
                global_configs(global_configs): configs of all participants for this dataset_job_stage
                event_time(datetime): optional; only works in STREAMING dataset,
                    event_time of current data_batch and job_stage

            Returns:
                dataset_job_stage(DatasetJobStage): dataset_job_stage which created in func
        """
        dataset_job: DatasetJob = self._session.query(DatasetJob).get(dataset_job_id)
        data_batch = DatasetService(session=self._session).get_data_batch(dataset=dataset_job.output_dataset,
                                                                          event_time=event_time)
        # create data_batch if not exist:
        if data_batch is None:
            batch_parameter = BatchParameter(dataset_id=dataset_job.output_dataset_id)
            if event_time:
                batch_parameter.event_time = to_timestamp(event_time)
                if dataset_job.is_daily_cron():
                    batch_parameter.cron_type = CronType.DAILY
                elif dataset_job.is_hourly_cron():
                    batch_parameter.cron_type = CronType.HOURLY
            data_batch = BatchService(self._session).create_batch(batch_parameter=batch_parameter)
            self._session.flush()
        dataset_job_stage = self._dataset_job_stage_service.create_dataset_job_stage_as_coordinator(
            project_id=dataset_job.project_id,
            dataset_job_id=dataset_job_id,
            output_data_batch_id=data_batch.id,
            global_configs=global_configs)
        return dataset_job_stage

    def create_data_batch_and_job_stage_as_participant(self,
                                                       dataset_job_id: int,
                                                       coordinator_id: int,
                                                       uuid: str,
                                                       name: str,
                                                       event_time: Optional[datetime] = None
                                                      ) -> Optional[DatasetJobStage]:
        """create data_batch and job_stage locally as participant

        UseCase 1: create new data_batch and new job_stage with given uuid and name:
            only called as role of participants, uuid and name are given by coordinator.
            will create both data_batch and job_stage

            Parameters:
                dataset_job_id(int): dataset_job id
                coordinator_id(int): id of coordinator
                uuid(str): uuid of dataset_job_stage
                name(str): name of dataset_job_stage
                event_time(datetime): optional; only works in STREAMING dataset,
                    event_time of current data_batch and job_stage

            Returns:
                dataset_job_stage(DatasetJobStage): dataset_job_stage which created in func

        UseCase 2: rerun data_batch:
            only called as role of participants, uuid and name are given by coordinator.
            aim to create a new job_stage when data_batch failed,
            will create only dataset_job_stage if find target data_batch

            Parameters:
                dataset_job_id(int): dataset_job id
                coordinator_id(int): id of coordinator
                uuid(str): uuid of dataset_job_stage
                name(str): name of dataset_job_stage
                event_time(datetime): optional; only works in STREAMING dataset,
                    event_time of current data_batch and job_stage

            Returns:
                dataset_job_stage(DatasetJobStage): dataset_job_stage which created in func
        """
        dataset_job: DatasetJob = self._session.query(DatasetJob).get(dataset_job_id)
        data_batch = DatasetService(session=self._session).get_data_batch(dataset=dataset_job.output_dataset,
                                                                          event_time=event_time)
        # create data_batch if not exist:
        if data_batch is None:
            batch_parameter = BatchParameter(dataset_id=dataset_job.output_dataset_id)
            if event_time:
                batch_parameter.event_time = to_timestamp(event_time)
                if dataset_job.is_daily_cron():
                    batch_parameter.cron_type = CronType.DAILY
                elif dataset_job.is_hourly_cron():
                    batch_parameter.cron_type = CronType.HOURLY
            data_batch = BatchService(self._session).create_batch(batch_parameter=batch_parameter)
            self._session.flush()
        dataset_job_stage = self._session.query(DatasetJobStage).filter(DatasetJobStage.uuid == uuid).first()
        # for idempotent, skip if dataset_job_stage exists:
        if dataset_job_stage is None:
            dataset_job_stage = self._dataset_job_stage_service.create_dataset_job_stage_as_participant(
                project_id=dataset_job.project_id,
                dataset_job_id=dataset_job_id,
                output_data_batch_id=data_batch.id,
                uuid=uuid,
                name=name,
                coordinator_id=coordinator_id)
        return dataset_job_stage

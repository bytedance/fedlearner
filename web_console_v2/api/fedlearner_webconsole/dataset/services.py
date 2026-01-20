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

import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Union
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload, Query

from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.review.ticket_helper import get_ticket_helper
from fedlearner_webconsole.utils.filtering import SupportedField, FieldType, FilterBuilder
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.flask_utils import get_current_user
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.utils.workflow import fill_variables
from fedlearner_webconsole.utils.pp_datetime import from_timestamp, to_timestamp, now
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.exceptions import (InvalidArgumentException, NotFoundException, MethodNotAllowedException,
                                              ResourceConflictException)
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.dataset.models import (DATASET_JOB_FINISHED_STATE, DATASET_STATE_CONVERT_MAP_V2,
                                                  LOCAL_DATASET_JOBS, MICRO_DATASET_JOB, DatasetFormat, ResourceState,
                                                  DatasetJobKind, DatasetJobStage, DatasetJobState, DatasetKindV2,
                                                  StoreFormat, DatasetType, Dataset, ImportType, DataBatch, DatasetJob,
                                                  DataSource, ProcessedDataset, DatasetJobSchedulerState)
from fedlearner_webconsole.dataset.meta_data import MetaData, ImageMetaData
from fedlearner_webconsole.dataset.delete_dependency import DatasetDeleteDependency
from fedlearner_webconsole.dataset.dataset_directory import DatasetDirectory
from fedlearner_webconsole.dataset.job_configer.dataset_job_configer import DatasetJobConfiger
from fedlearner_webconsole.dataset.filter_funcs import dataset_format_filter_op_equal, dataset_format_filter_op_in
from fedlearner_webconsole.dataset.util import get_dataset_path, parse_event_time_to_daily_folder_name, \
    parse_event_time_to_hourly_folder_name
from fedlearner_webconsole.dataset.metrics import emit_dataset_job_submission_store, emit_dataset_job_duration_store
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.proto.cleanup_pb2 import CleanupParameter, CleanupPayload
from fedlearner_webconsole.proto.dataset_pb2 import CronType, DatasetJobGlobalConfigs
from fedlearner_webconsole.proto import dataset_pb2
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterOp
from fedlearner_webconsole.proto.review_pb2 import TicketDetails, TicketType
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.cleanup.models import ResourceType
from fedlearner_webconsole.cleanup.services import CleanupService


class DataReader(object):

    def __init__(self, dataset_path: str):
        self._path = dataset_path
        self._dataset_directory = DatasetDirectory(dataset_path=dataset_path)
        self._file_manager = FileManager()

    # meta is generated from sparkapp/pipeline/analyzer.py
    def metadata(self, batch_name: str) -> MetaData:
        meta_path = self._dataset_directory.batch_meta_file(batch_name=batch_name)
        try:
            return MetaData(json.loads(self._file_manager.read(meta_path)))
        except Exception as e:  # pylint: disable=broad-except
            logging.info(f'failed to read meta file, path: {meta_path}, err: {e}')
            return MetaData()

    def image_metadata(self, thumbnail_dir_path: str, batch_name: str) -> ImageMetaData:
        meta_path = self._dataset_directory.batch_meta_file(batch_name=batch_name)
        try:
            return ImageMetaData(thumbnail_dir_path, json.loads(self._file_manager.read(meta_path)))
        except Exception as e:  # pylint: disable=broad-except
            logging.info(f'failed to read meta file, path: {meta_path}, err: {e}')
            return ImageMetaData(thumbnail_dir_path)


class DatasetService(object):

    DATASET_CLEANUP_DEFAULT_DELAY = timedelta(days=7)
    PUBLISHED_DATASET_FILTER_FIELDS = {
        'uuid':
            SupportedField(type=FieldType.STRING, ops={FilterOp.EQUAL: None}),
        'kind':
            SupportedField(type=FieldType.STRING, ops={
                FilterOp.IN: None,
                FilterOp.EQUAL: None
            }),
        'dataset_format':
            SupportedField(type=FieldType.STRING,
                           ops={
                               FilterOp.IN: dataset_format_filter_op_in,
                               FilterOp.EQUAL: dataset_format_filter_op_equal
                           }),
    }

    def __init__(self, session: Session):
        self._session = session
        self._file_manager = FileManager()
        self._published_dataset_filter_builder = FilterBuilder(model_class=Dataset,
                                                               supported_fields=self.PUBLISHED_DATASET_FILTER_FIELDS)

    @staticmethod
    def filter_dataset_state(query: Query, frontend_states: List[ResourceState]) -> Query:
        if len(frontend_states) == 0:
            return query
        dataset_job_states = []
        for k, v in DATASET_STATE_CONVERT_MAP_V2.items():
            if v in frontend_states:
                dataset_job_states.append(k)
        state_filter = DatasetJob.state.in_(dataset_job_states)
        # internal_processed dataset is now hack to succeeded,
        # so here we add all internal_processed dataset when filter succeeded dataset
        if ResourceState.SUCCEEDED in frontend_states:
            state_filter = or_(state_filter, Dataset.dataset_kind == DatasetKindV2.INTERNAL_PROCESSED)
        return query.filter(state_filter)

    def query_dataset_with_parent_job(self) -> Query:
        return self._session.query(Dataset).outerjoin(
            DatasetJob, and_(DatasetJob.output_dataset_id == Dataset.id, DatasetJob.input_dataset_id != Dataset.id))

    def create_dataset(self, dataset_parameter: dataset_pb2.DatasetParameter) -> Dataset:
        # check project existense
        project = self._session.query(Project).get(dataset_parameter.project_id)
        if project is None:
            raise NotFoundException(message=f'cannot found project with id: {dataset_parameter.project_id}')

        # Create dataset
        dataset = Dataset(
            name=dataset_parameter.name,
            uuid=dataset_parameter.uuid or resource_uuid(),
            is_published=dataset_parameter.is_published,
            dataset_type=DatasetType(dataset_parameter.type),
            comment=dataset_parameter.comment,
            project_id=dataset_parameter.project_id,
            dataset_kind=DatasetKindV2(dataset_parameter.kind),
            dataset_format=DatasetFormat[dataset_parameter.format].value,
            # set participant dataset creator_username to empty if dataset is created by coordinator
            # TODO(liuhehan): set participant dataset creator_username to username who authorize it
            creator_username=get_current_user().username if get_current_user() else '',
        )
        if dataset_parameter.path and dataset.dataset_kind in [
                DatasetKindV2.EXPORTED, DatasetKindV2.INTERNAL_PROCESSED
        ]:
            dataset.path = dataset_parameter.path
        else:
            dataset.path = get_dataset_path(dataset_name=dataset.name, uuid=dataset.uuid)
        if dataset_parameter.import_type:
            dataset.import_type = ImportType(dataset_parameter.import_type)
        if dataset_parameter.store_format:
            dataset.store_format = StoreFormat(dataset_parameter.store_format)
        if dataset_parameter.auth_status:
            dataset.auth_status = AuthStatus[dataset_parameter.auth_status]
        if dataset_parameter.creator_username:
            dataset.creator_username = dataset_parameter.creator_username
        elif get_current_user():
            dataset.creator_username = get_current_user().username
        meta_info = dataset_pb2.DatasetMetaInfo(need_publish=dataset_parameter.need_publish,
                                                value=dataset_parameter.value,
                                                schema_checkers=dataset_parameter.schema_checkers)
        dataset.set_meta_info(meta_info)
        self._session.add(dataset)
        return dataset

    def get_dataset(self, dataset_id: int = 0) -> Union[dict, dataset_pb2.Dataset]:
        dataset = self._session.query(Dataset).with_polymorphic([ProcessedDataset,
                                                                 Dataset]).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise NotFoundException(f'Failed to find dataset: {dataset_id}')
        return dataset.to_proto()

    def get_dataset_preview(self, dataset_id: int, batch_id: int) -> dict:
        batch = self._session.query(DataBatch).get(batch_id)
        if batch is None:
            raise NotFoundException(f'Failed to find data batch: {batch_id}')
        dataset = self._session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise NotFoundException(f'Failed to find dataset: {dataset_id}')
        reader = DataReader(dataset.path)
        if dataset.is_image():
            thumbnail_dir_path = DatasetDirectory(dataset_path=dataset.path).thumbnails_path(
                batch_name=batch.batch_name)
            meta = reader.image_metadata(thumbnail_dir_path=thumbnail_dir_path, batch_name=batch.batch_name)
        else:
            meta = reader.metadata(batch_name=batch.batch_name)
        return meta.get_preview()

    def feature_metrics(self, name: str, dataset_id: int, data_batch_id: int) -> dict:
        dataset = self._session.query(Dataset).get(dataset_id)
        if dataset is None:
            raise NotFoundException(f'Failed to find dataset: {dataset_id}')
        batch = self._session.query(DataBatch).get(data_batch_id)
        if batch is None:
            raise NotFoundException(f'Failed to find data batch: {data_batch_id}')
        meta = DataReader(dataset.path).metadata(batch_name=batch.batch_name)
        val = {}
        val['name'] = name
        val['metrics'] = meta.get_metrics_by_name(name)
        val['hist'] = meta.get_hist_by_name(name)
        return val

    def get_published_datasets(self,
                               project_id: int,
                               kind: Optional[DatasetJobKind] = None,
                               uuid: Optional[str] = None,
                               state: Optional[ResourceState] = None,
                               filter_exp: Optional[FilterExpression] = None,
                               time_range: Optional[timedelta] = None) -> List[dataset_pb2.ParticipantDatasetRef]:
        query = self.query_dataset_with_parent_job()
        query = query.options(joinedload(Dataset.data_batches))
        query = query.filter(Dataset.project_id == project_id)
        query = query.filter(Dataset.is_published.is_(True))
        if kind is not None:
            query = query.filter(Dataset.dataset_kind == kind)
        if uuid is not None:
            query = query.filter(Dataset.uuid == uuid)
        if state is not None:
            query = self.filter_dataset_state(query, frontend_states=[state])
        if filter_exp is not None:
            query = self._published_dataset_filter_builder.build_query(query, filter_exp)
        if time_range:
            query = query.filter(DatasetJob.time_range == time_range)
        query = query.order_by(Dataset.id.desc())
        datasets_ref = []
        for dataset in query.all():
            meta_info = dataset.get_meta_info()
            dataset_ref = dataset_pb2.ParticipantDatasetRef(
                uuid=dataset.uuid,
                name=dataset.name,
                format=DatasetFormat(dataset.dataset_format).name,
                file_size=dataset.get_file_size(),
                updated_at=to_timestamp(dataset.updated_at),
                value=meta_info.value,
                dataset_kind=dataset.dataset_kind.name,
                dataset_type=dataset.dataset_type.name,
                auth_status=dataset.auth_status.name if dataset.auth_status else '')
            datasets_ref.append(dataset_ref)
        return datasets_ref

    def publish_dataset(self, dataset_id: int, value: int = 0) -> Dataset:
        dataset: Dataset = self._session.query(Dataset).get(dataset_id)
        if not dataset:
            raise NotFoundException(f'Failed to find dataset: {dataset_id}')
        if dataset.dataset_kind != DatasetKindV2.RAW:
            raise MethodNotAllowedException(
                f'{dataset.dataset_kind.value} dataset cannot publish, dataset_id: {dataset.id}')
        dataset.is_published = True
        meta_info = dataset.get_meta_info()
        meta_info.value = value
        dataset.set_meta_info(meta_info)
        # TODO(liuhehan): a hack to add uuid for old dataset when publish, remove in the feature
        if dataset.uuid is None:
            dataset.uuid = resource_uuid()

        # create review ticket
        if dataset.ticket_uuid is None:
            ticket_helper = get_ticket_helper(session=self._session)
            ticket_helper.create_ticket(TicketType.PUBLISH_DATASET, TicketDetails(uuid=dataset.uuid))

        return dataset

    def withdraw_dataset(self, dataset_id: int):
        dataset = self._session.query(Dataset).get(dataset_id)
        if not dataset:
            raise NotFoundException(f'Failed to find dataset: {dataset_id}')
        dataset.is_published = False

        # reset ticket
        dataset.ticket_uuid = None
        dataset.ticket_status = None

    def cleanup_dataset(self, dataset: Dataset, delay_time: Optional[timedelta] = None) -> Tuple[bool, List[str]]:
        """ Register the dataset and underlying files to be cleaned with the cleanup module.

        Args:
            dataset: dataset which needs an exclusive lock to this row
            delay_time: delay time to start the cleanup task afterwards

        Raises:
            ResourceConflictException: if the `dataset` can not be deleted
        """
        if not delay_time:
            delay_time = self.DATASET_CLEANUP_DEFAULT_DELAY
        target_start_at = to_timestamp(now() + delay_time)
        is_deletable, error_msgs = DatasetDeleteDependency(self._session).is_deletable(dataset)
        if not is_deletable:
            error = {dataset.id: error_msgs}
            raise ResourceConflictException(f'{error}')
        logging.info(f'will mark the dataset:{dataset.id} is deleted')
        payload = CleanupPayload(paths=[dataset.path])
        dataset_cleanup_parm = CleanupParameter(resource_id=dataset.id,
                                                resource_type=ResourceType.DATASET.name,
                                                payload=payload,
                                                target_start_at=target_start_at)
        CleanupService(self._session).create_cleanup(cleanup_parmeter=dataset_cleanup_parm)
        dataset.deleted_at = now()
        logging.info(f'Has registered a cleanup for dataset:{dataset.id}')

    def get_data_batch(self, dataset: Dataset, event_time: Optional[datetime] = None) -> Optional[DataBatch]:
        if dataset.dataset_type == DatasetType.PSI:
            return self._session.query(DataBatch).filter(DataBatch.dataset_id == dataset.id).first()
        return self._session.query(DataBatch).filter(DataBatch.dataset_id == dataset.id).filter(
            DataBatch.event_time == event_time).first()


class DataSourceService(object):

    def __init__(self, session: Session):
        self._session = session

    def create_data_source(self, data_source_parameter: dataset_pb2.DataSource) -> DataSource:
        # check project existense
        project = self._session.query(Project).get(data_source_parameter.project_id)
        if project is None:
            raise NotFoundException(message=f'cannot found project with id: {data_source_parameter.project_id}')

        data_source = DataSource(
            name=data_source_parameter.name,
            comment=data_source_parameter.comment,
            uuid=resource_uuid(),
            is_published=False,
            path=data_source_parameter.url,
            project_id=data_source_parameter.project_id,
            creator_username=get_current_user().username,
            dataset_format=DatasetFormat[data_source_parameter.dataset_format].value,
            store_format=StoreFormat(data_source_parameter.store_format),
            dataset_type=DatasetType(data_source_parameter.dataset_type),
        )
        meta_info = dataset_pb2.DatasetMetaInfo(datasource_type=data_source_parameter.type,
                                                is_user_upload=data_source_parameter.is_user_upload,
                                                is_user_export=data_source_parameter.is_user_export)
        data_source.set_meta_info(meta_info)
        self._session.add(data_source)
        return data_source

    def get_data_sources(self, project_id: int) -> List[dataset_pb2.DataSource]:
        data_sources = self._session.query(DataSource).order_by(Dataset.created_at.desc())
        if project_id > 0:
            data_sources = data_sources.filter_by(project_id=project_id)
        data_source_ref = []
        for data_source in data_sources.all():
            # ignore user upload data_source and user export data_source
            meto_info = data_source.get_meta_info()
            if not meto_info.is_user_upload and not meto_info.is_user_export:
                data_source_ref.append(data_source.to_proto())
        return data_source_ref

    def delete_data_source(self, data_source_id: int):
        data_source = self._session.query(DataSource).get(data_source_id)
        if not data_source:
            raise NotFoundException(message=f'cannot find data_source with id: {data_source_id}')
        dataset_jobs = self._session.query(DatasetJob).filter_by(input_dataset_id=data_source.id).all()
        for dataset_job in dataset_jobs:
            if not dataset_job.is_finished():
                message = f'data_source {data_source.name} is still being processed by dataset_job {dataset_job.id}'
                logging.error(message)
                raise ResourceConflictException(message=message)

        data_source.deleted_at = now()


class BatchService(object):

    def __init__(self, session: Session):
        self._session = session

    def create_batch(self, batch_parameter: dataset_pb2.BatchParameter) -> DataBatch:
        dataset: Dataset = self._session.query(Dataset).filter_by(id=batch_parameter.dataset_id).first()
        if dataset is None:
            message = f'Failed to find dataset: {batch_parameter.dataset_id}'
            logging.error(message)
            raise NotFoundException(message=message)
        if dataset.dataset_type == DatasetType.PSI:
            # There should be one batch of a dataset in PSI mode.
            # So the naming convention of batch is `{dataset_path}/batch/0`.
            if len(dataset.data_batches) != 0:
                raise InvalidArgumentException(details='there should be one batch for PSI dataset')
            batch_folder_name = '0'
            event_time = None
        elif dataset.dataset_type == DatasetType.STREAMING:
            if batch_parameter.event_time == 0:
                raise InvalidArgumentException(
                    details='event time should be specified when create batch of streaming dataset')
            event_time = from_timestamp(batch_parameter.event_time)
            if batch_parameter.cron_type == CronType.DAILY:
                batch_folder_name = parse_event_time_to_daily_folder_name(event_time=event_time)
            elif batch_parameter.cron_type == CronType.HOURLY:
                batch_folder_name = parse_event_time_to_hourly_folder_name(event_time=event_time)
            else:
                # old data may not has cron_tpye, we just set to daily cron_type by default
                batch_folder_name = parse_event_time_to_daily_folder_name(event_time=event_time)
        batch_parameter.path = os.path.join(dataset.path, 'batch', batch_folder_name)
        # Create batch
        batch = DataBatch(dataset_id=dataset.id,
                          event_time=event_time,
                          comment=batch_parameter.comment,
                          path=batch_parameter.path,
                          name=batch_folder_name)
        self._session.add(batch)

        return batch

    def get_next_batch(self, data_batch: DataBatch) -> Optional[DataBatch]:
        parent_dataset_job_stage: DatasetJobStage = data_batch.latest_parent_dataset_job_stage
        if not parent_dataset_job_stage:
            logging.warning(f'not found parent_dataset_job_stage, data_batch id: {data_batch.id}')
            return None
        parent_dataset_job: DatasetJob = parent_dataset_job_stage.dataset_job
        if not parent_dataset_job:
            logging.warning(f'not found parent_dataset_job, data_batch id: {data_batch.id}')
            return None
        if not parent_dataset_job.is_cron():
            logging.warning(f'data_batch {data_batch.id} belongs to a non-cron dataset_job, has no next batch')
            return None
        next_time = data_batch.event_time + parent_dataset_job.time_range
        return self._session.query(DataBatch).filter(DataBatch.dataset_id == data_batch.dataset_id).filter(
            DataBatch.event_time == next_time).first()


class DatasetJobService(object):

    def __init__(self, session: Session):
        self._session = session

    def is_local(self, dataset_job_kind: DatasetJobKind) -> bool:
        return dataset_job_kind in LOCAL_DATASET_JOBS

    def need_distribute(self, dataset_job: DatasetJob) -> bool:
        # coordinator_id != 0 means it is a participant,
        # and dataset_job need to distribute when it has participants
        if dataset_job.coordinator_id != 0:
            return True
        return not self.is_local(dataset_job.kind)

    # filter participants which need to distribute dataset_job
    def get_participants_need_distribute(self, dataset_job: DatasetJob) -> List:
        participants = []
        if self.need_distribute(dataset_job):
            participants = ParticipantService(self._session).get_platform_participants_by_project(
                dataset_job.project_id)
        return participants

    def create_as_coordinator(self,
                              project_id: int,
                              kind: DatasetJobKind,
                              output_dataset_id: int,
                              global_configs: DatasetJobGlobalConfigs,
                              time_range: timedelta = None) -> DatasetJob:
        my_domain_name = SettingService.get_system_info().pure_domain_name
        input_dataset_uuid = global_configs.global_configs[my_domain_name].dataset_uuid
        input_dataset = self._session.query(Dataset).filter(Dataset.uuid == input_dataset_uuid).first()
        if input_dataset is None:
            raise InvalidArgumentException(f'failed to find dataset {input_dataset_uuid}')
        output_dataset = self._session.query(Dataset).get(output_dataset_id)
        if output_dataset is None:
            return InvalidArgumentException(details=f'failed to find dataset id {output_dataset_id}')
        configer = DatasetJobConfiger.from_kind(kind, self._session)
        config = configer.get_config()
        try:
            global_configs = configer.auto_config_variables(global_configs)
            fill_variables(config, global_configs.global_configs[my_domain_name].variables, dry_run=True)
        except TypeError as err:
            raise InvalidArgumentException(details=err.args) from err

        dataset_job = DatasetJob()
        dataset_job.uuid = resource_uuid()
        dataset_job.project_id = project_id
        dataset_job.coordinator_id = 0
        dataset_job.input_dataset_id = input_dataset.id
        dataset_job.output_dataset_id = output_dataset_id
        dataset_job.name = output_dataset.name
        dataset_job.kind = kind
        dataset_job.time_range = time_range
        dataset_job.set_global_configs(global_configs)
        dataset_job.set_context(dataset_pb2.DatasetJobContext(has_stages=True))
        current_user = get_current_user()
        if current_user is not None:
            dataset_job.creator_username = current_user.username

        self._session.add(dataset_job)

        emit_dataset_job_submission_store(uuid=dataset_job.uuid, kind=dataset_job.kind, coordinator_id=0)

        return dataset_job

    def create_as_participant(self,
                              project_id: int,
                              kind: DatasetJobKind,
                              global_configs: DatasetJobGlobalConfigs,
                              config: WorkflowDefinition,
                              output_dataset_id: int,
                              coordinator_id: int,
                              uuid: str,
                              creator_username: str,
                              time_range: timedelta = None) -> DatasetJob:
        my_domain_name = SettingService.get_system_info().pure_domain_name
        my_dataset_job_config = global_configs.global_configs[my_domain_name]

        input_dataset = self._session.query(Dataset).filter(Dataset.uuid == my_dataset_job_config.dataset_uuid).first()
        if input_dataset is None:
            return InvalidArgumentException(details=f'failed to find dataset {my_dataset_job_config.dataset_uuid}')
        output_dataset = self._session.query(Dataset).get(output_dataset_id)
        if output_dataset is None:
            return InvalidArgumentException(details=f'failed to find dataset id {output_dataset_id}')
        try:
            fill_variables(config, my_dataset_job_config.variables, dry_run=True)
        except TypeError as err:
            raise InvalidArgumentException(details=err.args) from err

        dataset_job = DatasetJob()
        dataset_job.uuid = uuid
        dataset_job.project_id = project_id
        dataset_job.input_dataset_id = input_dataset.id
        dataset_job.output_dataset_id = output_dataset_id
        dataset_job.name = output_dataset.name
        dataset_job.coordinator_id = coordinator_id
        dataset_job.kind = kind
        dataset_job.time_range = time_range
        dataset_job.creator_username = creator_username
        dataset_job.set_context(dataset_pb2.DatasetJobContext(has_stages=True))

        self._session.add(dataset_job)

        emit_dataset_job_submission_store(uuid=dataset_job.uuid,
                                          kind=dataset_job.kind,
                                          coordinator_id=dataset_job.coordinator_id)

        return dataset_job

    def start_dataset_job(self, dataset_job: DatasetJob):
        dataset_job.state = DatasetJobState.RUNNING
        dataset_job.started_at = now()

    def finish_dataset_job(self, dataset_job: DatasetJob, finish_state: DatasetJobState):
        if finish_state not in DATASET_JOB_FINISHED_STATE:
            raise ValueError(f'get invalid finish state: [{finish_state}] when try to finish dataset_job')
        dataset_job.state = finish_state
        dataset_job.finished_at = now()
        duration = to_timestamp(dataset_job.finished_at) - to_timestamp(dataset_job.created_at)
        emit_dataset_job_duration_store(duration=duration,
                                        uuid=dataset_job.uuid,
                                        kind=dataset_job.kind,
                                        coordinator_id=dataset_job.coordinator_id,
                                        state=finish_state)

    def start_cron_scheduler(self, dataset_job: DatasetJob):
        if not dataset_job.is_cron():
            logging.warning(f'[dataset_job_service]: failed to start schedule a non-cron dataset_job {dataset_job.id}')
            return
        dataset_job.scheduler_state = DatasetJobSchedulerState.RUNNABLE

    def stop_cron_scheduler(self, dataset_job: DatasetJob):
        if not dataset_job.is_cron():
            logging.warning(f'[dataset_job_service]: failed to stop schedule a non-cron dataset_job {dataset_job.id}')
            return
        dataset_job.scheduler_state = DatasetJobSchedulerState.STOPPED

    def delete_dataset_job(self, dataset_job: DatasetJob):
        if not dataset_job.is_finished():
            message = f'Failed to delete dataset_job: {dataset_job.id}; ' \
                f'reason: dataset_job state is {dataset_job.state.name}'
            logging.error(message)
            raise ResourceConflictException(message)
        dataset_job.deleted_at = now()


class DatasetJobStageService(object):

    def __init__(self, session: Session):
        self._session = session

    # TODO(liuhehan): delete in the near future after we use as_coordinator func
    def create_dataset_job_stage(self,
                                 project_id: int,
                                 dataset_job_id: int,
                                 output_data_batch_id: int,
                                 uuid: Optional[str] = None,
                                 name: Optional[str] = None):
        dataset_job: DatasetJob = self._session.query(DatasetJob).get(dataset_job_id)
        if dataset_job is None:
            raise InvalidArgumentException(details=f'failed to find dataset_job, id: {dataset_job_id}')
        output_data_batch: DataBatch = self._session.query(DataBatch).get(output_data_batch_id)
        if output_data_batch is None:
            raise InvalidArgumentException(details=f'failed to find output_data_batch, id: {output_data_batch_id}')

        dataset_job_stages: DatasetJobStage = self._session.query(DatasetJobStage).filter(
            DatasetJobStage.data_batch_id == output_data_batch_id).filter(
                DatasetJobStage.dataset_job_id == dataset_job_id).order_by(DatasetJobStage.created_at.desc()).all()
        index = len(dataset_job_stages)
        if index != 0 and not dataset_job_stages[0].is_finished():
            raise InvalidArgumentException(
                details=f'newest dataset_job_stage is still running, id: {dataset_job_stages[0].id}')

        dataset_job_stage = DatasetJobStage()
        dataset_job_stage.uuid = uuid or resource_uuid()
        dataset_job_stage.name = name or f'{output_data_batch.name}-stage{index}'
        dataset_job_stage.event_time = output_data_batch.event_time
        dataset_job_stage.dataset_job_id = dataset_job_id
        dataset_job_stage.data_batch_id = output_data_batch_id
        dataset_job_stage.project_id = project_id
        if dataset_job.coordinator_id == 0:
            dataset_job_stage.set_global_configs(dataset_job.get_global_configs())
        self._session.add(dataset_job_stage)

        self._session.flush()
        if dataset_job.kind not in MICRO_DATASET_JOB:
            output_data_batch.latest_parent_dataset_job_stage_id = dataset_job_stage.id
        elif dataset_job.kind == DatasetJobKind.ANALYZER:
            output_data_batch.latest_analyzer_dataset_job_stage_id = dataset_job_stage.id

        dataset_job.state = DatasetJobState.PENDING

        return dataset_job_stage

    def create_dataset_job_stage_as_coordinator(self, project_id: int, dataset_job_id: int, output_data_batch_id: int,
                                                global_configs: DatasetJobGlobalConfigs):
        dataset_job: DatasetJob = self._session.query(DatasetJob).get(dataset_job_id)
        if dataset_job is None:
            raise InvalidArgumentException(details=f'failed to find dataset_job, id: {dataset_job_id}')
        output_data_batch: DataBatch = self._session.query(DataBatch).get(output_data_batch_id)
        if output_data_batch is None:
            raise InvalidArgumentException(details=f'failed to find output_data_batch, id: {output_data_batch_id}')

        dataset_job_stages: DatasetJobStage = self._session.query(DatasetJobStage).filter(
            DatasetJobStage.data_batch_id == output_data_batch_id).filter(
                DatasetJobStage.dataset_job_id == dataset_job_id).order_by(DatasetJobStage.id.desc()).all()
        index = len(dataset_job_stages)
        if index != 0 and not dataset_job_stages[0].is_finished():
            raise InvalidArgumentException(
                details=f'newest dataset_job_stage is still running, id: {dataset_job_stages[0].id}')

        dataset_job_stage = DatasetJobStage()
        dataset_job_stage.uuid = resource_uuid()
        dataset_job_stage.name = f'{output_data_batch.name}-stage{index}'
        dataset_job_stage.event_time = output_data_batch.event_time
        dataset_job_stage.dataset_job_id = dataset_job_id
        dataset_job_stage.data_batch_id = output_data_batch_id
        dataset_job_stage.project_id = project_id
        dataset_job_stage.coordinator_id = 0
        dataset_job_stage.set_global_configs(global_configs)
        self._session.add(dataset_job_stage)

        self._session.flush()
        if dataset_job.kind not in MICRO_DATASET_JOB:
            output_data_batch.latest_parent_dataset_job_stage_id = dataset_job_stage.id
        elif dataset_job.kind == DatasetJobKind.ANALYZER:
            output_data_batch.latest_analyzer_dataset_job_stage_id = dataset_job_stage.id

        dataset_job.state = DatasetJobState.PENDING

        return dataset_job_stage

    def create_dataset_job_stage_as_participant(self, project_id: int, dataset_job_id: int, output_data_batch_id: int,
                                                uuid: str, name: str, coordinator_id: int):
        dataset_job: DatasetJob = self._session.query(DatasetJob).get(dataset_job_id)
        if dataset_job is None:
            raise InvalidArgumentException(details=f'failed to find dataset_job, id: {dataset_job_id}')
        output_data_batch: DataBatch = self._session.query(DataBatch).get(output_data_batch_id)
        if output_data_batch is None:
            raise InvalidArgumentException(details=f'failed to find output_data_batch, id: {output_data_batch_id}')

        dataset_job_stages: DatasetJobStage = self._session.query(DatasetJobStage).filter(
            DatasetJobStage.data_batch_id == output_data_batch_id).filter(
                DatasetJobStage.dataset_job_id == dataset_job_id).order_by(DatasetJobStage.id.desc()).all()
        index = len(dataset_job_stages)
        if index != 0 and not dataset_job_stages[0].is_finished():
            raise InvalidArgumentException(
                details=f'newest dataset_job_stage is still running, id: {dataset_job_stages[0].id}')

        dataset_job_stage = DatasetJobStage()
        dataset_job_stage.uuid = uuid
        dataset_job_stage.name = name
        dataset_job_stage.event_time = output_data_batch.event_time
        dataset_job_stage.dataset_job_id = dataset_job_id
        dataset_job_stage.data_batch_id = output_data_batch_id
        dataset_job_stage.project_id = project_id
        dataset_job_stage.coordinator_id = coordinator_id
        self._session.add(dataset_job_stage)

        self._session.flush()
        if dataset_job.kind not in MICRO_DATASET_JOB:
            output_data_batch.latest_parent_dataset_job_stage_id = dataset_job_stage.id
        elif dataset_job.kind == DatasetJobKind.ANALYZER:
            output_data_batch.latest_analyzer_dataset_job_stage_id = dataset_job_stage.id

        dataset_job.state = DatasetJobState.PENDING

        return dataset_job_stage

    def start_dataset_job_stage(self, dataset_job_stage: DatasetJobStage):
        dataset_job_stage.state = DatasetJobState.RUNNING
        dataset_job_stage.started_at = now()

        newest_job_stage_id, *_ = self._session.query(
            DatasetJobStage.id).filter(DatasetJobStage.dataset_job_id == dataset_job_stage.dataset_job_id).order_by(
                DatasetJobStage.created_at.desc()).first()
        if newest_job_stage_id == dataset_job_stage.id:
            dataset_job_stage.dataset_job.state = DatasetJobState.RUNNING

    def finish_dataset_job_stage(self, dataset_job_stage: DatasetJobStage, finish_state: DatasetJobState):
        if finish_state not in DATASET_JOB_FINISHED_STATE:
            raise ValueError(f'get invalid finish state: [{finish_state}] when try to finish dataset_job')
        dataset_job_stage.state = finish_state
        dataset_job_stage.finished_at = now()

        newest_job_stage_id, *_ = self._session.query(
            DatasetJobStage.id).filter(DatasetJobStage.dataset_job_id == dataset_job_stage.dataset_job_id).order_by(
                DatasetJobStage.created_at.desc()).first()
        if newest_job_stage_id == dataset_job_stage.id:
            dataset_job_stage.dataset_job.state = finish_state

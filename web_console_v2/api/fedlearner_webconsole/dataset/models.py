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

import enum
import os
from typing import Optional

from sqlalchemy.sql import func
from sqlalchemy import UniqueConstraint
from google.protobuf import text_format
from fedlearner_webconsole.dataset.consts import ERROR_BATCH_SIZE
from fedlearner_webconsole.proto import dataset_pb2
from fedlearner_webconsole.proto.dataset_pb2 import (DatasetJobGlobalConfigs, DatasetRef, DatasetMetaInfo,
                                                     DatasetJobContext, DatasetJobStageContext, TimeRange)
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.base_model.review_ticket_and_auth_model import ReviewTicketAndAuthModel
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.utils.base_model.softdelete_model import SoftDeleteModel
from fedlearner_webconsole.workflow.models import WorkflowExternalState


class DatasetType(enum.Enum):
    PSI = 'PSI'  # use PSI as none streaming dataset type
    STREAMING = 'STREAMING'


class BatchState(enum.Enum):
    NEW = 'NEW'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    IMPORTING = 'IMPORTING'
    UNKNOWN = 'UNKNOWN'


# used to represent dataset and data_batch frontend state
class ResourceState(enum.Enum):
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'


class PublishFrontendState(enum.Enum):
    UNPUBLISHED = 'UNPUBLISHED'
    TICKET_PENDING = 'TICKET_PENDING'
    TICKET_DECLINED = 'TICKET_DECLINED'
    PUBLISHED = 'PUBLISHED'


class DatasetFormat(enum.Enum):
    TABULAR = 0
    IMAGE = 1
    NONE_STRUCTURED = 2


class ImportType(enum.Enum):
    COPY = 'COPY'
    NO_COPY = 'NO_COPY'


class DatasetKindV2(enum.Enum):
    RAW = 'raw'
    PROCESSED = 'processed'
    SOURCE = 'source'
    EXPORTED = 'exported'
    INTERNAL_PROCESSED = 'internal_processed'  # dataset generatred by internal module, like model or tee


class DatasetSchemaChecker(enum.Enum):
    RAW_ID_CHECKER = 'RAW_ID_CHECKER'
    NUMERIC_COLUMNS_CHECKER = 'NUMERIC_COLUMNS_CHECKER'


class DatasetJobKind(enum.Enum):
    RSA_PSI_DATA_JOIN = 'RSA_PSI_DATA_JOIN'
    LIGHT_CLIENT_RSA_PSI_DATA_JOIN = 'LIGHT_CLIENT_RSA_PSI_DATA_JOIN'
    OT_PSI_DATA_JOIN = 'OT_PSI_DATA_JOIN'
    LIGHT_CLIENT_OT_PSI_DATA_JOIN = 'LIGHT_CLIENT_OT_PSI_DATA_JOIN'
    HASH_DATA_JOIN = 'HASH_DATA_JOIN'
    DATA_JOIN = 'DATA_JOIN'
    DATA_ALIGNMENT = 'DATA_ALIGNMENT'
    IMPORT_SOURCE = 'IMPORT_SOURCE'
    EXPORT = 'EXPORT'
    ANALYZER = 'ANALYZER'


# micro dataset_job's input/output dataset is the same one
MICRO_DATASET_JOB = [DatasetJobKind.ANALYZER]

LOCAL_DATASET_JOBS = [
    DatasetJobKind.IMPORT_SOURCE,
    DatasetJobKind.ANALYZER,
    DatasetJobKind.EXPORT,
    DatasetJobKind.LIGHT_CLIENT_OT_PSI_DATA_JOIN,
    DatasetJobKind.LIGHT_CLIENT_RSA_PSI_DATA_JOIN,
]


class DatasetJobState(enum.Enum):
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'
    STOPPED = 'STOPPED'


class StoreFormat(enum.Enum):
    UNKNOWN = 'UNKNOWN'
    CSV = 'CSV'
    TFRECORDS = 'TFRECORDS'


class DatasetJobSchedulerState(enum.Enum):
    PENDING = 'PENDING'
    RUNNABLE = 'RUNNABLE'
    STOPPED = 'STOPPED'


DATASET_STATE_CONVERT_MAP_V2 = {
    DatasetJobState.PENDING: ResourceState.PENDING,
    DatasetJobState.RUNNING: ResourceState.PROCESSING,
    DatasetJobState.SUCCEEDED: ResourceState.SUCCEEDED,
    DatasetJobState.FAILED: ResourceState.FAILED,
    DatasetJobState.STOPPED: ResourceState.FAILED,
}


class DataSourceType(enum.Enum):
    # hdfs datasource path, e.g. hdfs:///home/xxx
    HDFS = 'hdfs'
    # nfs datasource path, e.g. file:///data/xxx
    FILE = 'file'


SOURCE_IS_DELETED = 'deleted'
WORKFLOW_STATUS_STATE_MAPPER = {
    WorkflowExternalState.COMPLETED: ResourceState.SUCCEEDED,
    WorkflowExternalState.FAILED: ResourceState.FAILED,
    WorkflowExternalState.STOPPED: ResourceState.FAILED,
    WorkflowExternalState.INVALID: ResourceState.FAILED,
}
DATASET_JOB_FINISHED_STATE = [DatasetJobState.SUCCEEDED, DatasetJobState.FAILED, DatasetJobState.STOPPED]


class DataBatch(db.Model):
    __tablename__ = 'data_batches_v2'
    __table_args__ = (UniqueConstraint('event_time', 'dataset_id', name='uniq_event_time_dataset_id'),
                      default_table_args('This is webconsole dataset table'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id')
    name = db.Column(db.String(255), nullable=True, comment='data_batch name')
    event_time = db.Column(db.TIMESTAMP(timezone=True), nullable=True, comment='event_time')
    dataset_id = db.Column(db.Integer, nullable=False, comment='dataset_id')
    path = db.Column(db.String(512), comment='path')
    # TODO(wangsen.0914): gonna to deprecate
    state = db.Column(db.Enum(BatchState, native_enum=False, create_constraint=False),
                      default=BatchState.NEW,
                      comment='state')
    # move column will be deprecated after dataset refactor
    move = db.Column(db.Boolean, default=False, comment='move')
    # Serialized proto of DatasetBatch
    file_size = db.Column(db.BigInteger, default=0, comment='file_size in bytes')
    num_example = db.Column(db.BigInteger, default=0, comment='num_example')
    num_feature = db.Column(db.BigInteger, default=0, comment='num_feature')
    meta_info = db.Column(db.Text(16777215), comment='dataset meta info')
    comment = db.Column('cmt', db.Text(), key='comment', comment='comment')
    latest_parent_dataset_job_stage_id = db.Column(db.Integer,
                                                   nullable=False,
                                                   server_default=db.text('0'),
                                                   comment='latest parent dataset_job_stage id')
    latest_analyzer_dataset_job_stage_id = db.Column(db.Integer,
                                                     nullable=False,
                                                     server_default=db.text('0'),
                                                     comment='latest analyzer dataset_job_stage id')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created_at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           server_onupdate=func.now(),
                           comment='updated_at')
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted_at')

    dataset = db.relationship('Dataset',
                              primaryjoin='Dataset.id == '
                              'foreign(DataBatch.dataset_id)',
                              back_populates='data_batches')

    latest_parent_dataset_job_stage = db.relationship(
        'DatasetJobStage',
        primaryjoin='DatasetJobStage.id == foreign(DataBatch.latest_parent_dataset_job_stage_id)',
        # To disable the warning of back_populates
        overlaps='data_batch')

    @property
    def batch_name(self):
        return self.name or os.path.basename(os.path.abspath(self.path))

    def get_frontend_state(self) -> ResourceState:
        # use dataset_job state to replace dataset_job_stage state when dataset_job_stage not support
        if self.latest_parent_dataset_job_stage is None:
            return self.dataset.get_frontend_state()
        return DATASET_STATE_CONVERT_MAP_V2.get(self.latest_parent_dataset_job_stage.state)

    def is_available(self) -> bool:
        return self.get_frontend_state() == ResourceState.SUCCEEDED

    def to_proto(self) -> dataset_pb2.DataBatch:
        proto = dataset_pb2.DataBatch(id=self.id,
                                      name=self.batch_name,
                                      dataset_id=self.dataset_id,
                                      path=self.path,
                                      file_size=self.file_size,
                                      num_example=self.num_example,
                                      num_feature=self.num_feature,
                                      comment=self.comment,
                                      created_at=to_timestamp(self.created_at),
                                      updated_at=to_timestamp(self.updated_at),
                                      event_time=to_timestamp(self.event_time) if self.event_time else 0,
                                      latest_parent_dataset_job_stage_id=self.latest_parent_dataset_job_stage_id,
                                      latest_analyzer_dataset_job_stage_id=self.latest_analyzer_dataset_job_stage_id)
        proto.state = self.get_frontend_state().name
        return proto


class Dataset(SoftDeleteModel, ReviewTicketAndAuthModel, db.Model):
    __tablename__ = 'datasets_v2'
    __table_args__ = (default_table_args('This is webconsole dataset table'))

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id')
    uuid = db.Column(db.String(255), nullable=True, comment='dataset uuid')
    is_published = db.Column(db.Boolean, default=False, comment='dataset is published or not')
    name = db.Column(db.String(255), nullable=False, comment='dataset name')
    creator_username = db.Column(db.String(255), default='', comment='creator username')
    dataset_type = db.Column(db.Enum(DatasetType, native_enum=False, create_constraint=False),
                             default=DatasetType.PSI,
                             nullable=False,
                             comment='data type')
    path = db.Column(db.String(512), comment='dataset path')
    comment = db.Column('cmt', db.Text(), key='comment', comment='comment of dataset')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created time')
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           onupdate=func.now(),
                           comment='updated time')
    project_id = db.Column(db.Integer, default=0, comment='project_id')
    # New version of dataset kind
    dataset_kind = db.Column(db.Enum(DatasetKindV2, native_enum=False, length=32, create_constraint=False),
                             default=DatasetKindV2.RAW,
                             comment='new version of dataset kind, choices [raw, processed, ...]')
    # DatasetFormat enum
    dataset_format = db.Column(db.Integer, default=0, comment='dataset format')
    # StoreFormat
    store_format = db.Column(db.Enum(StoreFormat, native_enum=False, length=32, create_constraint=False),
                             default=StoreFormat.TFRECORDS,
                             comment='dataset store format, like CSV, TFRECORDS, ...')
    meta_info = db.Column(db.Text(16777215), comment='dataset meta info')

    import_type = db.Column(db.Enum(ImportType, length=64, native_enum=False, create_constraint=False),
                            server_default=ImportType.COPY.name,
                            comment='import type')

    data_batches = db.relationship('DataBatch',
                                   primaryjoin='foreign(DataBatch.dataset_id) == Dataset.id',
                                   order_by='desc(DataBatch.id)')
    project = db.relationship('Project', primaryjoin='foreign(Dataset.project_id) == Project.id')

    # dataset only has one main dataset_job as parent_dataset_job, but could have many micro dataset_job
    @property
    def parent_dataset_job(self):
        return None if not db.object_session(self) else db.object_session(self).query(DatasetJob).filter(
            DatasetJob.output_dataset_id == self.id).filter(
                DatasetJob.kind.not_in(MICRO_DATASET_JOB)).execution_options(include_deleted=True).first()

    # dataset only has one analyzer dataset_job
    def analyzer_dataset_job(self):
        return None if not db.object_session(self) else db.object_session(self).query(DatasetJob).filter(
            DatasetJob.output_dataset_id == self.id).filter(
                DatasetJob.kind == DatasetJobKind.ANALYZER).execution_options(include_deleted=True).first()

    # single table inheritance
    # Ref: https://docs.sqlalchemy.org/en/14/orm/inheritance.html
    __mapper_args__ = {'polymorphic_identity': DatasetKindV2.RAW, 'polymorphic_on': dataset_kind}

    def get_frontend_state(self) -> ResourceState:
        # if parent_dataset_job failed to generate, dataset state is failed
        if self.parent_dataset_job is None:
            return ResourceState.FAILED
        return DATASET_STATE_CONVERT_MAP_V2.get(self.parent_dataset_job.state)

    def get_file_size(self) -> int:
        file_size = 0
        for batch in self.data_batches:
            if not batch.file_size or batch.file_size == ERROR_BATCH_SIZE:
                continue
            file_size += batch.file_size
        return file_size

    def get_num_example(self) -> int:
        return sum([batch.num_example or 0 for batch in self.data_batches])

    def get_num_feature(self) -> int:
        if len(self.data_batches) != 0:
            # num_feature is decided by the first data_batch
            return self.data_batches[0].num_feature
        return 0

    # TODO(hangweiqiang): remove data_source after adapting fedlearner to dataset path
    def get_data_source(self) -> Optional[str]:
        if self.parent_dataset_job is not None:
            dataset_job_stage = db.object_session(self).query(DatasetJobStage).filter_by(
                dataset_job_id=self.parent_dataset_job.id).first()
            if dataset_job_stage is not None:
                return f'{dataset_job_stage.uuid}-psi-data-join-job'
            if self.parent_dataset_job.workflow is not None:
                return f'{self.parent_dataset_job.workflow.uuid}-psi-data-join-job'
        return None

    @property
    def publish_frontend_state(self) -> PublishFrontendState:
        if not self.is_published:
            return PublishFrontendState.UNPUBLISHED
        if self.ticket_status == TicketStatus.APPROVED:
            return PublishFrontendState.PUBLISHED
        if self.ticket_status == TicketStatus.DECLINED:
            return PublishFrontendState.TICKET_DECLINED
        return PublishFrontendState.TICKET_PENDING

    def to_ref(self) -> DatasetRef:
        # TODO(liuhehan): this is a lazy update of dataset store_format, remove it after release 2.4
        if self.dataset_kind in [DatasetKindV2.RAW, DatasetKindV2.PROCESSED] and self.store_format is None:
            self.store_format = StoreFormat.TFRECORDS
        # TODO(liuhehan): this is a lazy update for auth status, remove after release 2.4
        if self.auth_status is None:
            self.auth_status = AuthStatus.AUTHORIZED
        return DatasetRef(id=self.id,
                          uuid=self.uuid,
                          project_id=self.project_id,
                          name=self.name,
                          created_at=to_timestamp(self.created_at),
                          state_frontend=self.get_frontend_state().name,
                          path=self.path,
                          is_published=self.is_published,
                          dataset_format=DatasetFormat(self.dataset_format).name,
                          comment=self.comment,
                          dataset_kind=self.dataset_kind.name,
                          file_size=self.get_file_size(),
                          num_example=self.get_num_example(),
                          data_source=self.get_data_source(),
                          creator_username=self.creator_username,
                          dataset_type=self.dataset_type.name,
                          store_format=self.store_format.name if self.store_format else '',
                          import_type=self.import_type.name,
                          publish_frontend_state=self.publish_frontend_state.name,
                          auth_frontend_state=self.auth_frontend_state.name,
                          local_auth_status=self.auth_status.name,
                          participants_info=self.get_participants_info())

    def to_proto(self) -> dataset_pb2.Dataset:
        # TODO(liuhehan): this is a lazy update of dataset store_format, remove it after release 2.4
        if self.dataset_kind in [DatasetKindV2.RAW, DatasetKindV2.PROCESSED] and self.store_format is None:
            self.store_format = StoreFormat.TFRECORDS
        # TODO(liuhehan): this is a lazy update for auth status, remove after release 2.4
        if self.auth_status is None:
            self.auth_status = AuthStatus.AUTHORIZED
        meta_data = self.get_meta_info()
        analyzer_dataset_job = self.analyzer_dataset_job()
        # use newest data_batch updated_at time as dataset updated_at time if has data_batch
        updated_at = self.data_batches[0].updated_at if self.data_batches else self.updated_at
        return dataset_pb2.Dataset(
            id=self.id,
            uuid=self.uuid,
            is_published=self.is_published,
            project_id=self.project_id,
            name=self.name,
            workflow_id=self.parent_dataset_job.workflow_id if self.parent_dataset_job is not None else 0,
            path=self.path,
            created_at=to_timestamp(self.created_at),
            data_source=self.get_data_source(),
            file_size=self.get_file_size(),
            num_example=self.get_num_example(),
            comment=self.comment,
            num_feature=self.get_num_feature(),
            updated_at=to_timestamp(updated_at),
            deleted_at=to_timestamp(self.deleted_at) if self.deleted_at else None,
            parent_dataset_job_id=self.parent_dataset_job.id if self.parent_dataset_job is not None else 0,
            dataset_format=DatasetFormat(self.dataset_format).name,
            analyzer_dataset_job_id=analyzer_dataset_job.id if analyzer_dataset_job is not None else 0,
            state_frontend=self.get_frontend_state().name,
            dataset_kind=self.dataset_kind.name,
            value=meta_data.value,
            schema_checkers=meta_data.schema_checkers,
            creator_username=self.creator_username,
            import_type=self.import_type.name,
            dataset_type=self.dataset_type.name,
            store_format=self.store_format.name if self.store_format else '',
            publish_frontend_state=self.publish_frontend_state.name,
            auth_frontend_state=self.auth_frontend_state.name,
            local_auth_status=self.auth_status.name,
            participants_info=self.get_participants_info())

    def is_tabular(self) -> bool:
        return self.dataset_format == DatasetFormat.TABULAR.value

    def is_image(self) -> bool:
        return self.dataset_format == DatasetFormat.IMAGE.value

    def set_meta_info(self, meta: DatasetMetaInfo):
        if meta is None:
            meta = DatasetMetaInfo()
        self.meta_info = text_format.MessageToString(meta)

    def get_meta_info(self) -> DatasetMetaInfo:
        meta = DatasetMetaInfo()
        if self.meta_info is not None:
            meta = text_format.Parse(self.meta_info, DatasetMetaInfo())
        return meta

    def get_single_batch(self) -> DataBatch:
        """Get single batch of this dataset

        Returns:
            DataBatch: according data batch

        Raises:
            TypeError: when there's no data batch or more than one data batch
        """
        if not self.data_batches:
            raise TypeError(f'there is no data_batch for this dataset {self.id}')
        if len(self.data_batches) != 1:
            raise TypeError(f'there is more than one data_batch for this dataset {self.id}')
        return self.data_batches[0]


class DataSource(Dataset):

    __mapper_args__ = {'polymorphic_identity': DatasetKindV2.SOURCE}

    def to_proto(self) -> dataset_pb2.DataSource:
        meta_info = self.get_meta_info()
        return dataset_pb2.DataSource(
            id=self.id,
            comment=self.comment,
            uuid=self.uuid,
            name=self.name,
            type=meta_info.datasource_type,
            url=self.path,
            created_at=to_timestamp(self.created_at),
            project_id=self.project_id,
            is_user_upload=meta_info.is_user_upload,
            is_user_export=meta_info.is_user_export,
            creator_username=self.creator_username,
            dataset_format=DatasetFormat(self.dataset_format).name,
            store_format=self.store_format.name if self.store_format else '',
            dataset_type=self.dataset_type.name,
        )


class ProcessedDataset(Dataset):

    __mapper_args__ = {'polymorphic_identity': DatasetKindV2.PROCESSED}


class ExportedDataset(Dataset):

    __mapper_args__ = {'polymorphic_identity': DatasetKindV2.EXPORTED}


class InternalProcessedDataset(Dataset):

    __mapper_args__ = {'polymorphic_identity': DatasetKindV2.INTERNAL_PROCESSED}

    def get_frontend_state(self) -> ResourceState:
        # we just hack internal_processed dataset state to successded now
        return ResourceState.SUCCEEDED


class DatasetJob(SoftDeleteModel, db.Model):
    """ DatasetJob is the abstraction of basic action inside dataset module.

    UseCase 1: A import job from datasource to a dataset
    {
        "id": 1,
        "uuid": u456,
        "input_dataset_id": 5,
        "output_dataset_id": 4,
        "kind": "import_datasource",
        "global_configs": map<string, $ref:proto.DatasetJobConfig>,
        "workflow_id": 6,
        "coordinator_id": 0,
    }

    UseCase 2: A data join job between participants
    coodinator:
        {
            "id": 1,
            "uuid": u456,
            "input_dataset_id": 2,
            "output_dataset_id": 4,
            "kind": "rsa_psi_data_join",
            "global_configs": map<string, $ref:proto.DatasetJobConfig>,
            "coordinator_id": 0,
            "workflow_id": 6,
        }

    participant:
        {
            "id": 1,
            "uuid": u456,
            "input_dataset_id": 4,
            "output_dataset_id": 7,
            "kind": "rsa_psi_data_join",
            "global_configs": "",   # pull from coodinator
            "coordinator_id": 1,
            "workflow_id": 7,
        }
    """
    __tablename__ = 'dataset_jobs_v2'
    __table_args__ = (UniqueConstraint('uuid', name='uniq_dataset_job_uuid'), default_table_args('dataset_jobs_v2'))

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id of dataset job')
    uuid = db.Column(db.String(255), nullable=False, comment='dataset job uuid')
    name = db.Column(db.String(255), nullable=True, comment='dataset job name')

    # state is updated to keep the same with the newest dataset_job_stage
    state = db.Column(db.Enum(DatasetJobState, length=64, native_enum=False, create_constraint=False),
                      nullable=False,
                      default=DatasetJobState.PENDING,
                      comment='dataset job state')
    project_id = db.Column(db.Integer, nullable=False, comment='project id')

    # If multiple dataset/datasource input is supported, the following two columns will be deprecated.
    # Instead, a new table will be introduced.
    input_dataset_id = db.Column(db.Integer, nullable=False, comment='input dataset id')
    output_dataset_id = db.Column(db.Integer, nullable=False, comment='output dataset id')

    kind = db.Column(db.Enum(DatasetJobKind, length=128, native_enum=False, create_constraint=False),
                     nullable=False,
                     comment='dataset job kind')
    # If batch update mode is supported, this column will be deprecated.
    # Instead, a new table called DatasetStage and a new Column called Context will be introduced.
    workflow_id = db.Column(db.Integer, nullable=True, default=0, comment='relating workflow id')
    context = db.Column(db.Text(), nullable=True, default=None, comment='context info of dataset job')

    global_configs = db.Column(
        db.Text(), comment='global configs of this job including related participants only appear in coordinator')
    coordinator_id = db.Column(db.Integer, nullable=False, default=0, comment='participant id of this job coordinator')

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created time')
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           onupdate=func.now(),
                           comment='updated time')
    started_at = db.Column(db.DateTime(timezone=True), comment='started_at')
    finished_at = db.Column(db.DateTime(timezone=True), comment='finished_at')

    # cron_job will use time_range to infer event_time for next data_batch
    time_range = db.Column(db.Interval(native=False), nullable=True, comment='time_range to create new job_stage')
    # cron_job will read event_time to get current data_batch,
    # and update it to event_time + time_range when next new data_batch created
    event_time = db.Column(db.DateTime(timezone=True), nullable=True, comment='event_time for current data_batch')

    # scheduler_state will be filter and change by job_scheduler_v2
    scheduler_state = db.Column(db.Enum(DatasetJobSchedulerState, length=64, native_enum=False,
                                        create_constraint=False),
                                nullable=True,
                                default=DatasetJobSchedulerState.PENDING,
                                comment='dataset job scheduler state')

    creator_username = db.Column(db.String(255), nullable=True, comment='creator username')

    workflow = db.relationship('Workflow', primaryjoin='foreign(DatasetJob.workflow_id) == Workflow.id')
    project = db.relationship('Project', primaryjoin='foreign(DatasetJob.project_id) == Project.id')
    input_dataset = db.relationship('Dataset', primaryjoin='foreign(DatasetJob.input_dataset_id) == Dataset.id')

    @property
    def output_dataset(self):
        return None if not db.object_session(self) else db.object_session(self).query(Dataset).filter(
            Dataset.id == self.output_dataset_id).execution_options(include_deleted=True).first()

    dataset_job_stages = db.relationship(
        'DatasetJobStage',
        order_by='desc(DatasetJobStage.created_at)',
        primaryjoin='DatasetJob.id == foreign(DatasetJobStage.dataset_job_id)',
        # To disable the warning of back_populates
        overlaps='dataset_job')

    def get_global_configs(self) -> Optional[DatasetJobGlobalConfigs]:
        # For participant, global_config is empty text.
        if self.global_configs is None or len(self.global_configs) == 0:
            return None
        return text_format.Parse(self.global_configs, DatasetJobGlobalConfigs())

    def set_global_configs(self, global_configs: DatasetJobGlobalConfigs):
        self.global_configs = text_format.MessageToString(global_configs)

    def get_context(self) -> DatasetJobContext:
        context_pb = DatasetJobContext()
        if self.context:
            context_pb = text_format.Parse(self.context, context_pb)
        return context_pb

    def set_context(self, context: DatasetJobContext):
        self.context = text_format.MessageToString(context)

    def set_scheduler_message(self, scheduler_message: str):
        context_pb = self.get_context()
        context_pb.scheduler_message = scheduler_message
        self.set_context(context=context_pb)

    @property
    def time_range_pb(self) -> TimeRange:
        time_range_pb = TimeRange()
        if self.is_daily_cron():
            time_range_pb.days = self.time_range.days
        elif self.is_hourly_cron():
            # convert seconds to hours
            time_range_pb.hours = int(self.time_range.seconds / 3600)
        return time_range_pb

    def to_proto(self) -> dataset_pb2.DatasetJob:
        context = self.get_context()
        proto = dataset_pb2.DatasetJob(
            id=self.id,
            uuid=self.uuid,
            name=self.name,
            project_id=self.project_id,
            workflow_id=self.workflow_id,
            coordinator_id=self.coordinator_id,
            kind=self.kind.value,
            state=self.state.name,
            global_configs=self.get_global_configs(),
            input_data_batch_num_example=context.input_data_batch_num_example,
            output_data_batch_num_example=context.output_data_batch_num_example,
            has_stages=context.has_stages,
            created_at=to_timestamp(self.created_at),
            updated_at=to_timestamp(self.updated_at),
            started_at=to_timestamp(self.started_at) if self.started_at else 0,
            finished_at=to_timestamp(self.finished_at) if self.finished_at else 0,
            creator_username=self.creator_username,
            scheduler_state=self.scheduler_state.name if self.scheduler_state else '',
            time_range=self.time_range_pb,
            scheduler_message=context.scheduler_message,
        )
        if self.output_dataset:
            proto.result_dataset_uuid = self.output_dataset.uuid
            proto.result_dataset_name = self.output_dataset.name
        if self.workflow_id:
            proto.is_ready = True
        return proto

    def to_ref(self) -> dataset_pb2.DatasetJobRef:
        return dataset_pb2.DatasetJobRef(
            uuid=self.uuid,
            id=self.id,
            name=self.name,
            coordinator_id=self.coordinator_id,
            project_id=self.project_id,
            kind=self.kind.name,
            result_dataset_id=self.output_dataset_id,
            result_dataset_name=self.output_dataset.name if self.output_dataset else '',
            state=self.state.name,
            created_at=to_timestamp(self.created_at),
            has_stages=self.get_context().has_stages,
            creator_username=self.creator_username,
        )

    def is_coordinator(self) -> bool:
        return self.coordinator_id == 0

    def is_finished(self) -> bool:
        return self.state in DATASET_JOB_FINISHED_STATE

    def is_cron(self) -> bool:
        return self.time_range is not None

    def is_daily_cron(self) -> bool:
        if self.time_range is None:
            return False
        return self.time_range.days > 0

    def is_hourly_cron(self) -> bool:
        if self.time_range is None:
            return False
        # hourly time_range is less than one day
        return self.time_range.days == 0


class DatasetJobStage(SoftDeleteModel, db.Model):
    __tablename__ = 'dataset_job_stages_v2'
    __table_args__ = (UniqueConstraint('uuid',
                                       name='uniq_dataset_job_stage_uuid'), default_table_args('dataset_job_stages_v2'))

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id of dataset job stage')
    uuid = db.Column(db.String(255), nullable=False, comment='dataset job stage uuid')
    name = db.Column(db.String(255), nullable=True, comment='dataset job stage name')
    state = db.Column(db.Enum(DatasetJobState, length=64, native_enum=False, create_constraint=False),
                      nullable=False,
                      default=DatasetJobState.PENDING,
                      comment='dataset job stage state')
    project_id = db.Column(db.Integer, nullable=False, comment='project id')
    workflow_id = db.Column(db.Integer, nullable=True, default=0, comment='relating workflow id')
    dataset_job_id = db.Column(db.Integer, nullable=False, comment='dataset_job id')
    data_batch_id = db.Column(db.Integer, nullable=False, comment='data_batch id')
    event_time = db.Column(db.DateTime(timezone=True), nullable=True, comment='event_time of data upload')
    # store dataset_job global_configs to job_stage global_configs when job_stage created if is coordinator
    global_configs = db.Column(
        db.Text(), comment='global configs of this stage including related participants only appear in coordinator')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created time')
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           onupdate=func.now(),
                           comment='updated time')
    started_at = db.Column(db.DateTime(timezone=True), comment='started_at')
    finished_at = db.Column(db.DateTime(timezone=True), comment='finished_at')

    # dataset_job coordinator might be different with dataset_job_stage coordinator
    coordinator_id = db.Column(db.Integer,
                               nullable=False,
                               server_default=db.text('0'),
                               comment='participant id of this dataset_job_stage, 0 if it is coordinator')

    context = db.Column(db.Text(), nullable=True, default=None, comment='context info of dataset job stage')

    workflow = db.relationship('Workflow', primaryjoin='foreign(DatasetJobStage.workflow_id) == Workflow.id')
    project = db.relationship('Project', primaryjoin='foreign(DatasetJobStage.project_id) == Project.id')
    dataset_job = db.relationship('DatasetJob', primaryjoin='foreign(DatasetJobStage.dataset_job_id) == DatasetJob.id')
    data_batch = db.relationship('DataBatch', primaryjoin='foreign(DatasetJobStage.data_batch_id) == DataBatch.id')

    def get_global_configs(self) -> Optional[DatasetJobGlobalConfigs]:
        # For participant, global_config is empty text.
        if self.global_configs is None or len(self.global_configs) == 0:
            return None
        return text_format.Parse(self.global_configs, DatasetJobGlobalConfigs())

    def set_global_configs(self, global_configs: DatasetJobGlobalConfigs):
        self.global_configs = text_format.MessageToString(global_configs)

    def is_finished(self) -> bool:
        return self.state in DATASET_JOB_FINISHED_STATE

    def to_ref(self) -> dataset_pb2.DatasetJobStageRef:
        return dataset_pb2.DatasetJobStageRef(id=self.id,
                                              name=self.name,
                                              dataset_job_id=self.dataset_job_id,
                                              output_data_batch_id=self.data_batch_id,
                                              project_id=self.project_id,
                                              state=self.state.name,
                                              created_at=to_timestamp(self.created_at),
                                              kind=self.dataset_job.kind.name if self.dataset_job else '')

    def to_proto(self) -> dataset_pb2.DatasetJobStage:
        context = self.get_context()
        return dataset_pb2.DatasetJobStage(id=self.id,
                                           name=self.name,
                                           uuid=self.uuid,
                                           dataset_job_id=self.dataset_job_id,
                                           output_data_batch_id=self.data_batch_id,
                                           workflow_id=self.workflow_id,
                                           project_id=self.project_id,
                                           state=self.state.name,
                                           event_time=to_timestamp(self.event_time) if self.event_time else 0,
                                           global_configs=self.get_global_configs(),
                                           created_at=to_timestamp(self.created_at),
                                           updated_at=to_timestamp(self.updated_at),
                                           started_at=to_timestamp(self.started_at) if self.started_at else 0,
                                           finished_at=to_timestamp(self.finished_at) if self.finished_at else 0,
                                           dataset_job_uuid=self.dataset_job.uuid if self.dataset_job else None,
                                           is_ready=self.workflow is not None,
                                           kind=self.dataset_job.kind.name if self.dataset_job else '',
                                           input_data_batch_num_example=context.input_data_batch_num_example,
                                           output_data_batch_num_example=context.output_data_batch_num_example,
                                           scheduler_message=context.scheduler_message)

    def get_context(self) -> DatasetJobStageContext:
        context_pb = DatasetJobStageContext()
        if self.context:
            context_pb = text_format.Parse(self.context, context_pb)
        return context_pb

    def set_context(self, context: DatasetJobStageContext):
        self.context = text_format.MessageToString(context)

    def set_scheduler_message(self, scheduler_message: str):
        context_pb = self.get_context()
        context_pb.scheduler_message = scheduler_message
        self.set_context(context=context_pb)

    def is_coordinator(self) -> bool:
        return self.coordinator_id == 0

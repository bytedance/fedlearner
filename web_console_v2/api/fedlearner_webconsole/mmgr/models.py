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
import logging
from typing import Optional
from google.protobuf import text_format
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Index, UniqueConstraint
from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.algorithm.models import Algorithm, AlgorithmType
from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.mmgr.utils import get_job_path, get_exported_model_path, get_checkpoint_path, \
    get_output_path
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.utils.base_model import auth_model
from fedlearner_webconsole.utils.base_model.softdelete_model import SoftDeleteModel
from fedlearner_webconsole.utils.base_model.review_ticket_and_auth_model import ReviewTicketAndAuthModel
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.workflow.models import Workflow, WorkflowExternalState
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobPb, ModelJobGroupPb, ModelJobRef, ModelJobGroupRef, ModelPb, \
    ModelJobGlobalConfig, AlgorithmProjectList


class ModelType(enum.Enum):
    UNSPECIFIED = 0
    NN_MODEL = 1
    TREE_MODEL = 2


class ModelJobType(enum.Enum):
    UNSPECIFIED = 0
    NN_TRAINING = 1
    NN_EVALUATION = 2
    NN_PREDICTION = 3
    TREE_TRAINING = 4
    TREE_EVALUATION = 5
    TREE_PREDICTION = 6
    TRAINING = 7
    EVALUATION = 8
    PREDICTION = 9


class ModelJobRole(enum.Enum):
    PARTICIPANT = 0
    COORDINATOR = 1


class ModelJobStatus(enum.Enum):
    PENDING = 'PENDING'  # all model jobs are created, the local algorithm files and the local workflow are pending
    CONFIGURED = 'CONFIGURED'  # the local algorithm files are available and the local workflow is created
    ERROR = 'ERROR'  # error during creating model job
    RUNNING = 'RUNNING'
    STOPPED = 'STOPPED'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'  # job failed during running


class AuthStatus(enum.Enum):
    PENDING = 'PENDING'
    AUTHORIZED = 'AUTHORIZED'


class GroupCreateStatus(enum.Enum):
    PENDING = 'PENDING'
    FAILED = 'FAILED'
    SUCCEEDED = 'SUCCEEDED'


class GroupAuthFrontendStatus(enum.Enum):
    TICKET_PENDING = 'TICKET_PENDING'
    TICKET_DECLINED = 'TICKET_DECLINED'
    CREATE_PENDING = 'CREATE_PENDING'
    CREATE_FAILED = 'CREATE_FAILED'
    SELF_AUTH_PENDING = 'SELF_AUTH_PENDING'
    PART_AUTH_PENDING = 'PART_AUTH_PENDING'
    ALL_AUTHORIZED = 'ALL_AUTHORIZED'


class GroupAutoUpdateStatus(enum.Enum):
    INITIAL = 'INITIAL'
    ACTIVE = 'ACTIVE'
    STOPPED = 'STOPPED'


class ModelJobCreateStatus(enum.Enum):
    PENDING = 'PENDING'
    FAILED = 'FAILED'
    SUCCEEDED = 'SUCCEEDED'


class ModelJobAuthFrontendStatus(enum.Enum):
    TICKET_PENDING = 'TICKET_PENDING'
    TICKET_DECLINED = 'TICKET_DECLINED'
    CREATE_PENDING = 'CREATE_PENDING'
    CREATE_FAILED = 'CREATE_FAILED'
    SELF_AUTH_PENDING = 'SELF_AUTH_PENDING'
    PART_AUTH_PENDING = 'PART_AUTH_PENDING'
    ALL_AUTHORIZED = 'ALL_AUTHORIZED'


class ModelJob(db.Model, SoftDeleteModel, ReviewTicketAndAuthModel):
    __tablename__ = 'model_jobs_v2'
    __table_args__ = (Index('idx_uuid',
                            'uuid'), UniqueConstraint('job_name',
                                                      name='uniq_job_name'), default_table_args('model_jobs_v2'))

    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)
    name = db.Column(db.String(255), comment='name')
    uuid = db.Column(db.String(64), comment='uuid')
    role = db.Column(db.Enum(ModelJobRole, native_enum=False, length=32, create_constraint=False),
                     default=ModelJobRole.PARTICIPANT,
                     comment='role')
    model_job_type = db.Column(db.Enum(ModelJobType, native_enum=False, length=32, create_constraint=False),
                               default=ModelJobType.UNSPECIFIED,
                               comment='type')
    job_name = db.Column(db.String(255), comment='job_name')
    job_id = db.Column(db.Integer, comment='job id')
    # the model id used for prediction or evaluation
    model_id = db.Column(db.Integer, comment='model_id')
    group_id = db.Column(db.Integer, comment='group_id')
    project_id = db.Column(db.Integer, comment='project id')
    workflow_id = db.Column(db.Integer, comment='workflow id')
    workflow_uuid = db.Column(db.String(64), comment='workflow uuid')
    algorithm_type = db.Column(db.Enum(AlgorithmType, native_enum=False, length=32, create_constraint=False),
                               default=AlgorithmType.UNSPECIFIED,
                               comment='algorithm type')
    algorithm_id = db.Column(db.Integer, comment='algorithm id')
    dataset_id = db.Column(db.Integer, comment='dataset id')
    params = db.Column(db.Text(), comment='params')
    metrics = db.Column(db.Text(), comment='metrics')
    extra = db.Column(db.Text(), comment='extra')
    favorite = db.Column(db.Boolean, default=False, comment='favorite')
    comment = db.Column('cmt', db.Text(), key='comment', comment='comment')
    version = db.Column(db.Integer, comment='version')
    creator_username = db.Column(db.String(255), comment='creator username')
    coordinator_id = db.Column(db.Integer, comment='coordinator participant id')
    path = db.Column('fspath', db.String(512), key='path', comment='model job path')
    metric_is_public = db.Column(db.Boolean(), default=False, comment='is metric public')
    global_config = db.Column(db.Text(16777215), comment='global_config')
    status = db.Column(db.Enum(ModelJobStatus, native_enum=False, length=32, create_constraint=False),
                       default=ModelJobStatus.PENDING,
                       comment='model job status')
    create_status = db.Column(db.Enum(ModelJobCreateStatus, native_enum=False, length=32, create_constraint=False),
                              default=ModelJobCreateStatus.PENDING,
                              comment='create status')
    auth_status = db.Column(db.Enum(AuthStatus, native_enum=False, length=32, create_constraint=False),
                            default=AuthStatus.PENDING,
                            comment='authorization status')
    auto_update = db.Column(db.Boolean(), server_default=db.text('0'), comment='is auto update')
    data_batch_id = db.Column(db.Integer, comment='data_batches id for auto update job')
    error_message = db.Column(db.Text(), comment='error message')
    created_at = db.Column(db.DateTime(timezone=True), comment='created_at', server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated_at',
                           server_default=func.now(),
                           onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted_at')
    # the model id used for prediction or evaluation
    model = db.relationship('Model', primaryjoin='Model.id == foreign(ModelJob.model_id)')
    group = db.relationship('ModelJobGroup', primaryjoin='ModelJobGroup.id == foreign(ModelJob.group_id)')
    project = db.relationship(Project.__name__, primaryjoin='Project.id == foreign(ModelJob.project_id)')
    # job_name is the foreign key, job_id is unknown when creating
    job = db.relationship('Job', primaryjoin='Job.name == foreign(ModelJob.job_name)')
    # workflow_uuid is the foreign key, workflow_id is unknown when creating
    workflow = db.relationship(Workflow.__name__, primaryjoin='Workflow.uuid == foreign(ModelJob.workflow_uuid)')
    algorithm = db.relationship(Algorithm.__name__, primaryjoin='Algorithm.id == foreign(ModelJob.algorithm_id)')
    dataset = db.relationship(Dataset.__name__, primaryjoin='Dataset.id == foreign(ModelJob.dataset_id)')
    data_batch = db.relationship('DataBatch', primaryjoin='DataBatch.id == foreign(ModelJob.data_batch_id)')

    output_model = db.relationship(
        'Model',
        uselist=False,
        primaryjoin='ModelJob.id == foreign(Model.model_job_id)',
        # To disable the warning of back_populates
        overlaps='model_job')

    def to_proto(self) -> ModelJobPb:
        config = self.config()
        model_job = ModelJobPb(
            id=self.id,
            name=self.name,
            uuid=self.uuid,
            role=self.role.name,
            model_job_type=self.model_job_type.name,
            algorithm_type=self.algorithm_type.name if self.algorithm_type else AlgorithmType.UNSPECIFIED.name,
            algorithm_id=self.algorithm_id,
            group_id=self.group_id,
            project_id=self.project_id,
            state=self.state.name,
            configured=config is not None,
            model_id=self.model_id,
            model_name=self.model_name(),
            job_id=self.job_id,
            job_name=self.job_name,
            workflow_id=self.workflow_id,
            dataset_id=self.dataset_id,
            dataset_name=self.dataset_name(),
            creator_username=self.creator_username,
            coordinator_id=self.coordinator_id,
            auth_status=self.auth_status.name if self.auth_status else '',
            status=self.status.name if self.status else '',
            error_message=self.error_message,
            auto_update=self.auto_update,
            data_batch_id=self.data_batch_id,
            created_at=to_timestamp(self.created_at),
            updated_at=to_timestamp(self.updated_at),
            started_at=self.started_at(),
            stopped_at=self.stopped_at(),
            version=self.version,
            comment=self.comment,
            metric_is_public=self.metric_is_public,
            global_config=self.get_global_config(),
            participants_info=self.get_participants_info(),
            auth_frontend_status=self.get_model_job_auth_frontend_status().name)
        if config is not None:
            model_job.config.MergeFrom(config)
        if self.output_model is not None:
            model_job.output_model_name = self.output_model.name
            model_job.output_models.append(self.output_model.to_proto())
        return model_job

    def to_ref(self) -> ModelJobRef:
        return ModelJobRef(
            id=self.id,
            name=self.name,
            uuid=self.uuid,
            group_id=self.group_id,
            project_id=self.project_id,
            role=self.role.name,
            model_job_type=self.model_job_type.name,
            algorithm_type=self.algorithm_type.name if self.algorithm_type else AlgorithmType.UNSPECIFIED.name,
            algorithm_id=self.algorithm_id,
            state=self.state.name,
            configured=self.config() is not None,
            creator_username=self.creator_username,
            coordinator_id=self.coordinator_id,
            created_at=to_timestamp(self.created_at),
            updated_at=to_timestamp(self.updated_at),
            started_at=self.started_at(),
            stopped_at=self.stopped_at(),
            version=self.version,
            metric_is_public=self.metric_is_public,
            status=self.status.name if self.status else '',
            auto_update=self.auto_update,
            auth_status=self.auth_status.name if self.auth_status else '',
            participants_info=self.get_participants_info(),
            auth_frontend_status=self.get_model_job_auth_frontend_status().name)

    @property
    def state(self) -> WorkflowExternalState:
        # TODO(hangweiqiang): design model job state
        if self.workflow is None:
            return WorkflowExternalState.PENDING_ACCEPT
        return self.workflow.get_state_for_frontend()

    def get_model_job_auth_frontend_status(self) -> ModelJobAuthFrontendStatus:
        if self.ticket_status == TicketStatus.PENDING:
            if self.ticket_uuid is not None:
                return ModelJobAuthFrontendStatus.TICKET_PENDING
            # Update old data that is set to PENDING by default when ticket is disabled
            self.ticket_status = TicketStatus.APPROVED
        if self.ticket_status == TicketStatus.DECLINED:
            return ModelJobAuthFrontendStatus.TICKET_DECLINED
        if self.auth_status not in [AuthStatus.AUTHORIZED]:
            return ModelJobAuthFrontendStatus.SELF_AUTH_PENDING
        if self.is_all_participants_authorized():
            return ModelJobAuthFrontendStatus.ALL_AUTHORIZED
        if self.create_status in [ModelJobCreateStatus.PENDING]:
            return ModelJobAuthFrontendStatus.CREATE_PENDING
        if self.create_status in [ModelJobCreateStatus.FAILED]:
            return ModelJobAuthFrontendStatus.CREATE_FAILED
        return ModelJobAuthFrontendStatus.PART_AUTH_PENDING

    def get_job_path(self):
        path = self.project.get_storage_root_path(None)
        if path is None:
            logging.warning('cannot find storage_root_path')
            return None
        return get_job_path(path, self.job_name)

    def get_exported_model_path(self) -> Optional[str]:
        """Get the path of the exported models.

        Returns:
            The path of the exported_models is returned. Return None if the
            path can not found. There may be multiple checkpoints under the
            path. The file structure of nn_model under the path of
            exported_model is
            - exported_models:
              - ${terminated time, e.g. 1619769879}
                - _SUCCESS
                  - saved_model.pb
                  - variables
                    - variables.data-00000-of-00001
                    - variables.index
        """
        job_path = self.get_job_path()
        if job_path is None:
            return None
        return get_exported_model_path(job_path)

    def get_checkpoint_path(self):
        job_path = self.get_job_path()
        if job_path is None:
            return None
        return get_checkpoint_path(job_path=job_path)

    def get_output_path(self):
        job_path = self.get_job_path()
        if job_path is None:
            return None
        return get_output_path(job_path)

    def model_name(self) -> Optional[str]:
        if self.model_id is not None:
            return self.model.name
        return None

    def dataset_name(self) -> Optional[str]:
        # checking through relationship instead of existence of id, since item is possibly deleted
        if self.dataset is not None:
            return self.dataset.name
        return None

    def started_at(self) -> Optional[int]:
        if self.workflow:
            return self.workflow.start_at
        return None

    def stopped_at(self) -> Optional[int]:
        if self.workflow:
            return self.workflow.stop_at
        return None

    def config(self) -> Optional[WorkflowDefinition]:
        if self.workflow:
            return self.workflow.get_config()
        return None

    def is_deletable(self) -> bool:
        return self.state in [
            WorkflowExternalState.FAILED, WorkflowExternalState.STOPPED, WorkflowExternalState.COMPLETED
        ]

    def set_global_config(self, proto: ModelJobGlobalConfig):
        self.global_config = text_format.MessageToString(proto)

    def get_global_config(self) -> Optional[ModelJobGlobalConfig]:
        if self.global_config is not None:
            return text_format.Parse(self.global_config, ModelJobGlobalConfig())
        return None


class Model(db.Model, SoftDeleteModel):
    __tablename__ = 'models_v2'
    __table_args__ = (UniqueConstraint('name', name='uniq_name'), UniqueConstraint('uuid', name='uniq_uuid'),
                      default_table_args('models_v2'))

    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)
    name = db.Column(db.String(255), comment='name')
    uuid = db.Column(db.String(64), comment='uuid')
    algorithm_type = db.Column(db.Enum(AlgorithmType, native_enum=False, length=32, create_constraint=False),
                               default=AlgorithmType.UNSPECIFIED,
                               comment='algorithm type')
    # TODO(hangweiqiang): remove model_type coloumn
    model_type = db.Column(db.Enum(ModelType, native_enum=False, length=32, create_constraint=False),
                           default=ModelType.UNSPECIFIED,
                           comment='type')
    model_path = db.Column(db.String(512), comment='model path')
    favorite = db.Column(db.Boolean, default=False, comment='favorite model')
    comment = db.Column('cmt', db.Text(), key='comment', comment='comment')
    group_id = db.Column(db.Integer, comment='group_id')
    project_id = db.Column(db.Integer, comment='project_id')
    job_id = db.Column(db.Integer, comment='job id')
    model_job_id = db.Column(db.Integer, comment='model job id')
    version = db.Column(db.Integer, comment='version')
    created_at = db.Column(db.DateTime(timezone=True), comment='created_at', server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated_at',
                           server_default=func.now(),
                           onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted_at')
    group = db.relationship('ModelJobGroup', primaryjoin='ModelJobGroup.id == foreign(Model.group_id)')
    project = db.relationship('Project', primaryjoin='Project.id == foreign(Model.project_id)')
    job = db.relationship('Job', primaryjoin='Job.id == foreign(Model.job_id)')
    # the model_job generating this model
    model_job = db.relationship('ModelJob', primaryjoin='ModelJob.id == foreign(Model.model_job_id)')
    # the model_jobs inheriting this model
    derived_model_jobs = db.relationship(
        'ModelJob',
        primaryjoin='foreign(ModelJob.model_id) == Model.id',
        # To disable the warning of back_populates
        overlaps='model')

    def to_proto(self) -> ModelPb:
        return ModelPb(
            id=self.id,
            name=self.name,
            uuid=self.uuid,
            algorithm_type=self.algorithm_type.name if self.algorithm_type else AlgorithmType.UNSPECIFIED.name,
            group_id=self.group_id,
            project_id=self.project_id,
            model_job_id=self.model_job_id,
            model_job_name=self.model_job_name(),
            job_id=self.job_id,
            job_name=self.job_name(),
            workflow_id=self.workflow_id(),
            workflow_name=self.workflow_name(),
            version=self.version,
            created_at=to_timestamp(self.created_at),
            updated_at=to_timestamp(self.updated_at),
            comment=self.comment,
            model_path=self.model_path)

    def workflow_id(self):
        if self.job is not None:
            return self.job.workflow_id
        return None

    def job_name(self):
        if self.job is not None:
            return self.job.name
        return None

    def workflow_name(self):
        if self.job is not None:
            return self.job.workflow.name
        return None

    def model_job_name(self):
        if self.model_job is not None:
            return self.model_job.name
        return None

    def get_exported_model_path(self):
        """Get the path of the exported models
        same with get_exported_path function in ModelJob class
        """
        return get_exported_model_path(self.model_path)

    def get_checkpoint_path(self):
        return get_checkpoint_path(self.model_path)


class ModelJobGroup(db.Model, SoftDeleteModel, ReviewTicketAndAuthModel):
    # inconsistency between table name and class name due to historical issues
    __tablename__ = 'model_groups_v2'
    __table_args__ = (UniqueConstraint('name', name='uniq_name'), default_table_args('model_groups_v2'))

    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)
    uuid = db.Column(db.String(64), comment='uuid')
    name = db.Column(db.String(255), comment='name')
    project_id = db.Column(db.Integer, comment='project_id')
    role = db.Column(db.Enum(ModelJobRole, native_enum=False, length=32, create_constraint=False),
                     default=ModelJobRole.PARTICIPANT,
                     comment='role')
    authorized = db.Column(db.Boolean, default=False, comment='authorized to participants in project')
    dataset_id = db.Column(db.Integer, comment='dataset id')
    algorithm_type = db.Column(db.Enum(AlgorithmType, native_enum=False, length=32, create_constraint=False),
                               default=AlgorithmType.UNSPECIFIED,
                               comment='algorithm type')
    algorithm_project_id = db.Column(db.Integer, comment='algorithm project id')
    algorithm_id = db.Column(db.Integer, comment='algorithm id')
    config = db.Column(db.Text(16777215), comment='config')
    cron_job_global_config = db.Column(db.Text(16777215), comment='global config for cron job')
    # use proto.AlgorithmProjectList to store the algorithm project uuid of each participant
    algorithm_project_uuid_list = db.Column('algorithm_uuid_list',
                                            db.Text(16777215),
                                            key='algorithm_uuid_list',
                                            comment='algorithm project uuid for all participants')
    comment = db.Column('cmt', db.Text(), key='comment', comment='comment')
    creator_username = db.Column(db.String(255), comment='creator username')
    coordinator_id = db.Column(db.Integer, comment='coordinator participant id')
    cron_config = db.Column(db.String(255), comment='cron expression in UTC timezone')
    path = db.Column('fspath', db.String(512), key='path', comment='model job group path')
    _auth_status = db.Column('auth_status',
                             db.Enum(auth_model.AuthStatus, native_enum=False, length=32, create_constraint=False),
                             default=auth_model.AuthStatus.PENDING,
                             comment='auth status')
    auto_update_status = db.Column(db.Enum(GroupAutoUpdateStatus, native_enum=False, length=32,
                                           create_constraint=False),
                                   default=GroupAutoUpdateStatus.INITIAL,
                                   comment='auto update status')
    start_data_batch_id = db.Column(db.Integer, comment='start data_batches id for auto update job')
    created_at = db.Column(db.DateTime(timezone=True), comment='created_at', server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated_at',
                           server_default=func.now(),
                           onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted_at')
    extra = db.Column(db.Text(), comment='extra')  # json string
    latest_version = db.Column(db.Integer, default=0, comment='latest version')
    status = db.Column(db.Enum(GroupCreateStatus, native_enum=False, length=32, create_constraint=False),
                       default=GroupCreateStatus.PENDING,
                       comment='create status')
    project = db.relationship('Project', primaryjoin='Project.id == foreign(ModelJobGroup.project_id)')
    algorithm = db.relationship('Algorithm', primaryjoin='Algorithm.id == foreign(ModelJobGroup.algorithm_id)')
    algorithm_project = db.relationship(
        'AlgorithmProject', primaryjoin='AlgorithmProject.id == foreign(ModelJobGroup.algorithm_project_id)')
    dataset = db.relationship('Dataset', primaryjoin='Dataset.id == foreign(ModelJobGroup.dataset_id)')
    model_jobs = db.relationship(
        'ModelJob',
        order_by='desc(ModelJob.version)',
        primaryjoin='ModelJobGroup.id == foreign(ModelJob.group_id)',
        # To disable the warning of back_populates
        overlaps='group')
    start_data_batch = db.relationship('DataBatch',
                                       primaryjoin='DataBatch.id == foreign(ModelJobGroup.start_data_batch_id)')

    @property
    def auth_status(self):
        if self._auth_status is not None:
            return self._auth_status
        if self.authorized:
            return auth_model.AuthStatus.AUTHORIZED
        return auth_model.AuthStatus.PENDING

    @auth_status.setter
    def auth_status(self, auth_status: auth_model.AuthStatus):
        self._auth_status = auth_status

    def to_ref(self) -> ModelJobGroupRef:
        group = ModelJobGroupRef(id=self.id,
                                 name=self.name,
                                 uuid=self.uuid,
                                 role=self.role.name,
                                 project_id=self.project_id,
                                 authorized=self.authorized,
                                 algorithm_type=self.algorithm_type.name,
                                 configured=self.config is not None,
                                 creator_username=self.creator_username,
                                 coordinator_id=self.coordinator_id,
                                 latest_version=self.latest_version,
                                 participants_info=self.get_participants_info(),
                                 auth_status=self.auth_status.name,
                                 created_at=to_timestamp(self.created_at),
                                 updated_at=to_timestamp(self.updated_at))
        latest_job_state = self.latest_job_state()
        if latest_job_state is not None:
            group.latest_job_state = latest_job_state.name
        group.auth_frontend_status = self.get_group_auth_frontend_status().name
        return group

    def to_proto(self) -> ModelJobGroupPb:
        group = ModelJobGroupPb(id=self.id,
                                name=self.name,
                                uuid=self.uuid,
                                role=self.role.name,
                                project_id=self.project_id,
                                authorized=self.authorized,
                                dataset_id=self.dataset_id,
                                algorithm_type=self.algorithm_type.name,
                                algorithm_project_id=self.algorithm_project_id,
                                algorithm_id=self.algorithm_id,
                                configured=self.config is not None,
                                creator_username=self.creator_username,
                                coordinator_id=self.coordinator_id,
                                cron_config=self.cron_config,
                                latest_version=self.latest_version,
                                participants_info=self.get_participants_info(),
                                algorithm_project_uuid_list=self.get_algorithm_project_uuid_list(),
                                auth_status=self.auth_status.name,
                                auto_update_status=self.auto_update_status.name if self.auto_update_status else '',
                                start_data_batch_id=self.start_data_batch_id,
                                created_at=to_timestamp(self.created_at),
                                updated_at=to_timestamp(self.updated_at),
                                comment=self.comment)
        latest_job_state = self.latest_job_state()
        if latest_job_state is not None:
            group.latest_job_state = latest_job_state.name
        group.auth_frontend_status = self.get_group_auth_frontend_status().name
        if self.config is not None:
            group.config.MergeFrom(self.get_config())
        group.model_jobs.extend([mj.to_ref() for mj in self.model_jobs])
        return group

    def latest_job_state(self) -> Optional[ModelJobStatus]:
        if len(self.model_jobs) == 0:
            return None
        return self.model_jobs[0].status

    def get_group_auth_frontend_status(self) -> GroupAuthFrontendStatus:
        if self.ticket_status == TicketStatus.PENDING:
            if self.ticket_uuid is not None:
                return GroupAuthFrontendStatus.TICKET_PENDING
            # Update old data that is set to PENDING by default when ticket is disabled
            self.ticket_status = TicketStatus.APPROVED
        if self.ticket_status == TicketStatus.DECLINED:
            return GroupAuthFrontendStatus.TICKET_DECLINED
        if not self.authorized:
            return GroupAuthFrontendStatus.SELF_AUTH_PENDING
        if self.is_all_participants_authorized():
            return GroupAuthFrontendStatus.ALL_AUTHORIZED
        if self.status == GroupCreateStatus.PENDING:
            return GroupAuthFrontendStatus.CREATE_PENDING
        if self.status == GroupCreateStatus.FAILED:
            return GroupAuthFrontendStatus.CREATE_FAILED
        return GroupAuthFrontendStatus.PART_AUTH_PENDING

    def get_config(self) -> Optional[WorkflowDefinition]:
        if self.config is not None:
            return text_format.Parse(self.config, WorkflowDefinition())
        return None

    def set_config(self, config: Optional[WorkflowDefinition] = None):
        if config is None:
            config = WorkflowDefinition()
        self.config = text_format.MessageToString(config)

    def is_deletable(self) -> bool:
        for model_job in self.model_jobs:
            if not model_job.is_deletable():
                return False
        return True

    def latest_completed_job(self) -> Optional[ModelJob]:
        for job in self.model_jobs:
            if job.state == WorkflowExternalState.COMPLETED:
                return job
        return None

    def set_algorithm_project_uuid_list(self, proto: AlgorithmProjectList):
        self.algorithm_project_uuid_list = text_format.MessageToString(proto)

    def get_algorithm_project_uuid_list(self) -> AlgorithmProjectList:
        algorithm_project_uuid_list = AlgorithmProjectList()
        if self.algorithm_project_uuid_list is not None:
            algorithm_project_uuid_list = text_format.Parse(self.algorithm_project_uuid_list, AlgorithmProjectList())
        return algorithm_project_uuid_list


def is_federated(algorithm_type: AlgorithmType, model_job_type: ModelJobType) -> bool:
    return algorithm_type != AlgorithmType.NN_HORIZONTAL or model_job_type == ModelJobType.TRAINING

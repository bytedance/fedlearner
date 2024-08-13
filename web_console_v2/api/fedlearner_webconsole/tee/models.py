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
from google.protobuf import text_format
from typing import List, Optional
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Index

from fedlearner_webconsole.algorithm.models import Algorithm
from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.tee_pb2 import TrustedJobGroupPb, TrustedJobGroupRef, TrustedJobPb, TrustedJobRef, \
    Resource, ParticipantDatasetList, TrustedNotification
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.base_model.review_ticket_and_auth_model import ReviewTicketAndAuthModel
from fedlearner_webconsole.job.models import JobState, Job


class GroupCreateStatus(enum.Enum):
    PENDING = 'PENDING'
    FAILED = 'FAILED'
    SUCCEEDED = 'SUCCEEDED'


class TicketAuthStatus(enum.Enum):
    TICKET_PENDING = 'TICKET_PENDING'
    TICKET_DECLINED = 'TICKET_DECLINED'
    CREATE_PENDING = 'CREATE_PENDING'
    CREATE_FAILED = 'CREATE_FAILED'
    AUTH_PENDING = 'AUTH_PENDING'
    AUTHORIZED = 'AUTHORIZED'


class TrustedJobStatus(enum.Enum):
    NEW = 'NEW'
    CREATED = 'CREATED'
    CREATE_FAILED = 'CREATE_FAILED'
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'
    STOPPED = 'STOPPED'


class TrustedJobType(enum.Enum):
    ANALYZE = 'ANALYZE'
    EXPORT = 'EXPORT'


class TrustedJobGroup(db.Model, ReviewTicketAndAuthModel):
    __tablename__ = 'trusted_job_groups_v2'
    __table_args__ = (
        Index('idx_trusted_group_name', 'name'),
        Index('idx_trusted_group_project_id', 'project_id'),
        default_table_args('trusted_job_groups_v2'),
    )
    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)
    name = db.Column(db.String(255), comment='name')
    uuid = db.Column(db.String(64), comment='uuid')
    latest_version = db.Column(db.Integer, default=0, comment='latest version')
    comment = db.Column('cmt', db.Text(), key='comment', comment='comment of trusted job group')
    project_id = db.Column(db.Integer, comment='project id')
    created_at = db.Column(db.DateTime(timezone=True), comment='created at', server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated at',
                           server_default=func.now(),
                           onupdate=func.now())
    creator_username = db.Column(db.String(255), comment='creator username')
    coordinator_id = db.Column(db.Integer, comment='coordinator participant id')
    analyzer_id = db.Column(db.Integer, comment='analyzer participant id')
    status = db.Column(db.Enum(GroupCreateStatus, native_enum=False, length=32, create_constraint=False),
                       default=GroupCreateStatus.PENDING,
                       comment='create state')
    unauth_participant_ids = db.Column(db.Text(), comment='unauth participant ids')
    algorithm_uuid = db.Column(db.String(64), comment='algorithm uuid')
    resource = db.Column('rsc', db.String(255), comment='resource')
    dataset_id = db.Column(db.Integer, comment='dataset id')
    participant_datasets = db.Column(db.Text(), comment='list of participant-to-dataset mapping')
    # relationship to other tables
    project = db.relationship(Project.__name__, primaryjoin='Project.id == foreign(TrustedJobGroup.project_id)')
    algorithm = db.relationship(Algorithm.__name__,
                                primaryjoin='Algorithm.uuid == foreign(TrustedJobGroup.algorithm_uuid)')
    trusted_jobs = db.relationship(
        'TrustedJob',
        order_by='desc(TrustedJob.version)',
        primaryjoin='TrustedJobGroup.id == foreign(TrustedJob.trusted_job_group_id)',
        # To disable the warning of back_populates
        overlaps='group')
    dataset = db.relationship(Dataset.__name__, primaryjoin='Dataset.id == foreign(TrustedJobGroup.dataset_id)')

    def to_proto(self) -> TrustedJobGroupPb:
        group = TrustedJobGroupPb(
            id=self.id,
            name=self.name,
            uuid=self.uuid,
            latest_version=self.latest_version,
            comment=self.comment,
            project_id=self.project_id,
            created_at=to_timestamp(self.created_at),
            updated_at=to_timestamp(self.updated_at),
            creator_username=self.creator_username,
            coordinator_id=self.coordinator_id,
            analyzer_id=self.analyzer_id,
            ticket_uuid=self.ticket_uuid,
            ticket_status=self.ticket_status.name,
            status=self.status.name,
            auth_status=self.auth_status.name,
            ticket_auth_status=self.get_ticket_auth_status().name,
            latest_job_status=self.get_latest_job_status().name,
            algorithm_id=self.algorithm.id if self.algorithm else 0,
            algorithm_uuid=self.algorithm_uuid,
            dataset_id=self.dataset_id,
        )
        if self.unauth_participant_ids is not None:
            group.unauth_participant_ids.extend(self.get_unauth_participant_ids())
        if self.resource is not None:
            group.resource.MergeFrom(self.get_resource())
        if self.participant_datasets is not None:
            group.participant_datasets.MergeFrom(self.get_participant_datasets())
        return group

    def to_ref(self) -> TrustedJobGroupRef:
        group = TrustedJobGroupRef(
            id=self.id,
            name=self.name,
            created_at=to_timestamp(self.created_at),
            ticket_status=self.ticket_status.name,
            status=self.status.name,
            auth_status=self.auth_status.name,
            ticket_auth_status=self.get_ticket_auth_status().name,
            latest_job_status=self.get_latest_job_status().name,
            is_configured=self.resource is not None,
        )
        if self.coordinator_id == 0:
            group.is_creator = True
        else:
            group.is_creator = False
            group.creator_id = self.coordinator_id
        group.unauth_participant_ids.extend(self.get_unauth_participant_ids())
        return group

    def get_latest_job_status(self) -> TrustedJobStatus:
        for trusted_job in self.trusted_jobs:
            if trusted_job.type == TrustedJobType.ANALYZE:
                return trusted_job.get_status()
        return TrustedJobStatus.NEW

    def get_ticket_auth_status(self) -> TicketAuthStatus:
        if self.ticket_status == TicketStatus.PENDING:
            return TicketAuthStatus.TICKET_PENDING
        if self.ticket_status == TicketStatus.DECLINED:
            return TicketAuthStatus.TICKET_DECLINED
        if self.status == GroupCreateStatus.PENDING:
            return TicketAuthStatus.CREATE_PENDING
        if self.status == GroupCreateStatus.FAILED:
            return TicketAuthStatus.CREATE_FAILED
        if self.auth_status != AuthStatus.AUTHORIZED or len(self.get_unauth_participant_ids()) > 0:
            return TicketAuthStatus.AUTH_PENDING
        return TicketAuthStatus.AUTHORIZED

    def get_resource(self) -> Optional[Resource]:
        if self.resource is not None:
            return text_format.Parse(self.resource, Resource())
        return None

    def set_resource(self, resource: Optional[Resource] = None):
        if resource is None:
            resource = Resource()
        self.resource = text_format.MessageToString(resource)

    def get_participant_datasets(self) -> Optional[ParticipantDatasetList]:
        if self.participant_datasets is not None:
            return text_format.Parse(self.participant_datasets, ParticipantDatasetList())
        return None

    def set_participant_datasets(self, participant_datasets: Optional[ParticipantDatasetList] = None):
        if participant_datasets is None:
            participant_datasets = ParticipantDatasetList()
        self.participant_datasets = text_format.MessageToString(participant_datasets)

    def get_unauth_participant_ids(self) -> List[int]:
        if self.unauth_participant_ids is not None and self.unauth_participant_ids:
            sids = self.unauth_participant_ids.split(',')
            return [int(s) for s in sids]
        return []

    def set_unauth_participant_ids(self, ids: List[int]):
        if len(ids) > 0:
            self.unauth_participant_ids = ','.join([str(i) for i in ids])
        else:
            self.unauth_participant_ids = None

    def is_deletable(self) -> bool:
        for trusted_job in self.trusted_jobs:
            if trusted_job.get_status() in [TrustedJobStatus.PENDING, TrustedJobStatus.RUNNING]:
                return False
        return True

    def to_notification(self) -> TrustedNotification:
        return TrustedNotification(
            type=TrustedNotification.TRUSTED_JOB_GROUP_CREATE,
            id=self.id,
            name=self.name,
            created_at=to_timestamp(self.created_at),
            coordinator_id=self.coordinator_id,
        )


class TrustedJob(db.Model, ReviewTicketAndAuthModel):
    __tablename__ = 'trusted_jobs_v2'
    __table_args__ = (
        Index('idx_trusted_name', 'name'),
        Index('idx_trusted_project_id', 'project_id'),
        default_table_args('trusted_jobs_v2'),
    )
    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)
    name = db.Column(db.String(255), comment='name')
    type = db.Column('trusted_job_type',
                     db.Enum(TrustedJobType, native_enum=False, length=32, create_constraint=False),
                     default=TrustedJobType.ANALYZE,
                     key='type',
                     comment='trusted job type')
    job_id = db.Column(db.Integer, comment='job id')
    uuid = db.Column(db.String(64), comment='uuid')
    version = db.Column(db.Integer, comment='version')
    export_count = db.Column(db.Integer, default=0, comment='export count')
    comment = db.Column('cmt', db.Text(), key='comment', comment='comment of trusted job')
    project_id = db.Column(db.Integer, comment='project id')
    trusted_job_group_id = db.Column(db.Integer, comment='trusted job group id')
    coordinator_id = db.Column(db.Integer, comment='coordinator participant id')
    created_at = db.Column(db.DateTime(timezone=True), comment='created at', server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated at',
                           server_default=func.now(),
                           onupdate=func.now())
    started_at = db.Column(db.DateTime(timezone=True), comment='started_at')
    finished_at = db.Column(db.DateTime(timezone=True), comment='finished_at')
    status = db.Column(db.Enum(TrustedJobStatus, native_enum=False, length=32, create_constraint=False),
                       default=TrustedJobStatus.NEW,
                       comment='trusted job status')
    algorithm_uuid = db.Column(db.String(64), comment='algorithm uuid')
    resource = db.Column('rsc', db.String(255), comment='resource')
    export_dataset_id = db.Column(db.Integer, comment='export dataset id')
    result_key = db.Column(db.Text(), comment='result key')
    # relationship to other tables
    job = db.relationship(Job.__name__, primaryjoin='Job.id == foreign(TrustedJob.job_id)')
    project = db.relationship(Project.__name__, primaryjoin='Project.id == foreign(TrustedJob.project_id)')
    group = db.relationship('TrustedJobGroup',
                            primaryjoin='TrustedJobGroup.id == foreign(TrustedJob.trusted_job_group_id)')
    algorithm = db.relationship(Algorithm.__name__, primaryjoin='Algorithm.uuid == foreign(TrustedJob.algorithm_uuid)')
    export_dataset = db.relationship(Dataset.__name__,
                                     primaryjoin='Dataset.id == foreign(TrustedJob.export_dataset_id)')

    def to_proto(self) -> TrustedJobPb:
        trusted_job = TrustedJobPb(
            id=self.id,
            type=self.type.name,
            name=self.name,
            job_id=self.job_id,
            uuid=self.uuid,
            version=self.version,
            comment=self.comment,
            project_id=self.project_id,
            trusted_job_group_id=self.trusted_job_group_id,
            coordinator_id=self.coordinator_id,
            status=self.get_status().name,
            created_at=to_timestamp(self.created_at),
            updated_at=to_timestamp(self.updated_at),
            started_at=to_timestamp(self.started_at) if self.started_at is not None else None,
            finished_at=to_timestamp(self.finished_at) if self.finished_at is not None else None,
            algorithm_id=self.algorithm.id if self.algorithm else 0,
            algorithm_uuid=self.algorithm_uuid,
            ticket_uuid=self.ticket_uuid,
            ticket_status=self.ticket_status.name,
            auth_status=self.auth_status.name,
            participants_info=self.get_participants_info(),
            ticket_auth_status=self.get_ticket_auth_status().name,
            export_dataset_id=self.export_dataset_id,
        )
        if self.resource is not None:
            trusted_job.resource.MergeFrom(self.get_resource())
        return trusted_job

    def to_ref(self) -> TrustedJobRef:
        return TrustedJobRef(
            id=self.id,
            type=self.type.name,
            name=self.name,
            coordinator_id=self.coordinator_id,
            job_id=self.job_id,
            comment=self.comment,
            status=self.get_status().name,
            participants_info=self.get_participants_info(),
            ticket_auth_status=self.get_ticket_auth_status().name,
            started_at=to_timestamp(self.started_at) if self.started_at is not None else None,
            finished_at=to_timestamp(self.finished_at) if self.finished_at is not None else None,
        )

    def get_resource(self) -> Optional[Resource]:
        if self.resource is not None:
            return text_format.Parse(self.resource, Resource())
        return None

    def set_resource(self, resource: Optional[Resource] = None):
        if resource is None:
            resource = Resource()
        self.resource = text_format.MessageToString(resource)

    def update_status(self):
        if self.status in [TrustedJobStatus.FAILED, TrustedJobStatus.STOPPED, TrustedJobStatus.SUCCEEDED]:
            return
        if self.job is None:
            return
        job_state = self.job.state
        if job_state == JobState.FAILED:
            self.status = TrustedJobStatus.FAILED
        if job_state == JobState.COMPLETED:
            self.status = TrustedJobStatus.SUCCEEDED
        if job_state == JobState.STARTED:
            self.status = TrustedJobStatus.RUNNING
        if job_state == job_state.STOPPED:
            self.status = TrustedJobStatus.STOPPED
        if job_state in [JobState.NEW, JobState.WAITING]:
            self.status = TrustedJobStatus.PENDING
        if self.status in [TrustedJobStatus.FAILED, TrustedJobStatus.STOPPED, TrustedJobStatus.SUCCEEDED]:
            self.finished_at = self.job.updated_at

    def get_status(self) -> TrustedJobStatus:
        self.update_status()
        return self.status

    def to_notification(self) -> TrustedNotification:
        return TrustedNotification(
            type=TrustedNotification.TRUSTED_JOB_EXPORT,
            id=self.id,
            name=f'{self.group.name}-{self.name}',
            created_at=to_timestamp(self.created_at),
            coordinator_id=self.coordinator_id,
        )

    def get_ticket_auth_status(self) -> TicketAuthStatus:
        if self.ticket_status == TicketStatus.PENDING:
            return TicketAuthStatus.TICKET_PENDING
        if self.ticket_status == TicketStatus.DECLINED:
            return TicketAuthStatus.TICKET_DECLINED
        if self.status == TrustedJobStatus.NEW:
            return TicketAuthStatus.CREATE_PENDING
        if self.status == TrustedJobStatus.CREATE_FAILED:
            return TicketAuthStatus.CREATE_FAILED
        if not self.is_all_participants_authorized():
            return TicketAuthStatus.AUTH_PENDING
        return TicketAuthStatus.AUTHORIZED

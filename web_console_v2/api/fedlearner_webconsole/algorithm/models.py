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

import os
import enum
from typing import Optional
from sqlalchemy.sql.schema import Index, UniqueConstraint
from google.protobuf import text_format
from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmParameter, PendingAlgorithmPb, AlgorithmPb, \
    AlgorithmProjectPb
from fedlearner_webconsole.utils.pp_datetime import now, to_timestamp
from fedlearner_webconsole.utils.base_model.softdelete_model import SoftDeleteModel
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus, ReviewTicketModel


def normalize_path(path: str) -> str:
    if path.startswith('hdfs://'):
        return path
    if path.startswith('file://'):
        _, pure_path = path.split('://')
        return f'file://{os.path.normpath(pure_path)}'
    return os.path.normpath(path)


class AlgorithmType(enum.Enum):
    UNSPECIFIED = 0
    NN_LOCAL = 1
    NN_HORIZONTAL = 2
    NN_VERTICAL = 3
    TREE_VERTICAL = 4
    TRUSTED_COMPUTING = 5


class Source(enum.Enum):
    UNSPECIFIED = 0
    PRESET = 1
    USER = 2
    THIRD_PARTY = 3  # deprecated
    PARTICIPANT = 4  # algorithm from participant


class ReleaseStatus(enum.Enum):
    UNPUBLISHED = 0  # deprecated
    PUBLISHED = 1  # deprecated
    UNRELEASED = 'UNRELEASED'
    RELEASED = 'RELEASED'


class PublishStatus(enum.Enum):
    UNPUBLISHED = 'UNPUBLISHED'
    PUBLISHED = 'PUBLISHED'


class AlgorithmStatus(enum.Enum):
    UNPUBLISHED = 'UNPUBLISHED'
    PENDING_APPROVAL = 'PENDING_APPROVAL'
    APPROVED = 'APPROVED'
    DECLINED = 'DECLINED'
    PUBLISHED = 'PUBLISHED'


# TODO(hangweiqiang): read https://docs.sqlalchemy.org/en/14/orm/inheritance.html and try refactor
class AlgorithmProject(db.Model, SoftDeleteModel):
    __tablename__ = 'algorithm_projects_v2'
    __table_args__ = (UniqueConstraint('name', 'source', 'project_id', name='uniq_name_source_project_id'),
                      UniqueConstraint('uuid', name='uniq_uuid'), default_table_args('algorithm_projects'))
    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)
    uuid = db.Column(db.String(64), comment='uuid')
    name = db.Column(db.String(255), comment='name')
    project_id = db.Column(db.Integer, comment='project id')
    latest_version = db.Column(db.Integer, default=0, comment='latest version')
    type = db.Column('algorithm_type',
                     db.Enum(AlgorithmType, native_enum=False, length=32, create_constraint=False),
                     default=AlgorithmType.UNSPECIFIED,
                     key='type',
                     comment='algorithm type')
    source = db.Column(db.Enum(Source, native_enum=False, length=32, create_constraint=False),
                       default=Source.UNSPECIFIED,
                       comment='algorithm source')
    # Algorithm project publish has been modified to release. Algorithm project is unreleased when file or
    # parameter is edited. In order to ensure compatibility, it is still saved as publish_status in the database,
    # and _release_status is added to the model layer to make a conversion when data is used.
    _release_status = db.Column('publish_status',
                                db.Enum(ReleaseStatus, native_enum=False, length=32, create_constraint=False),
                                default=ReleaseStatus.UNRELEASED,
                                comment='release status')
    publish_status = db.Column('publish_status_v2',
                               db.Enum(PublishStatus, native_enum=False, length=32, create_constraint=False),
                               server_default=PublishStatus.UNPUBLISHED.name,
                               comment='publish status')
    username = db.Column(db.String(255), comment='creator name')
    participant_id = db.Column(db.Integer, comment='participant id')
    path = db.Column('fspath', db.String(512), key='path', comment='algorithm project path')
    parameter = db.Column(db.Text(), comment='parameter')
    comment = db.Column('cmt', db.String(255), key='comment', comment='comment')
    created_at = db.Column(db.DateTime(timezone=True), default=now, comment='created time')
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now, comment='updated time')
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted time')
    project = db.relationship(Project.__name__, primaryjoin='foreign(AlgorithmProject.project_id) == Project.id')
    user = db.relationship(User.__name__, primaryjoin='foreign(AlgorithmProject.username) == User.username')
    participant = db.relationship(Participant.__name__,
                                  primaryjoin='foreign(AlgorithmProject.participant_id) == Participant.id')
    algorithms = db.relationship(
        'Algorithm',
        order_by='desc(Algorithm.version)',
        primaryjoin='foreign(Algorithm.algorithm_project_id) == AlgorithmProject.id',
        # To disable the warning of back_populates
        overlaps='algorithm_project')

    @property
    def release_status(self) -> ReleaseStatus:
        if self._release_status == ReleaseStatus.UNPUBLISHED:
            return ReleaseStatus.UNRELEASED
        if self._release_status == ReleaseStatus.PUBLISHED:
            return ReleaseStatus.RELEASED
        return self._release_status

    @release_status.setter
    def release_status(self, release_status: ReleaseStatus):
        self._release_status = release_status

    def set_parameter(self, parameter: Optional[AlgorithmParameter] = None):
        if parameter is None:
            parameter = AlgorithmParameter()
        self.parameter = text_format.MessageToString(parameter)

    def get_parameter(self) -> Optional[AlgorithmParameter]:
        if self.parameter is not None:
            return text_format.Parse(self.parameter, AlgorithmParameter())
        return None

    def is_path_accessible(self, path: str):
        if self.path is None:
            return False
        return normalize_path(path).startswith(self.path)

    def get_participant_name(self):
        if self.participant is not None:
            return self.participant.name
        return None

    def to_proto(self) -> AlgorithmProjectPb:
        return AlgorithmProjectPb(
            id=self.id,
            uuid=self.uuid,
            name=self.name,
            project_id=self.project_id,
            latest_version=self.latest_version,
            type=self.type.name,
            source=self.source.name,
            publish_status=self.publish_status.name,
            release_status=self.release_status.name,
            username=self.username,
            participant_id=self.participant_id,
            participant_name=self.get_participant_name(),
            path=self.path,
            parameter=self.get_parameter(),
            comment=self.comment,
            created_at=to_timestamp(self.created_at) if self.created_at else None,
            updated_at=to_timestamp(self.updated_at) if self.updated_at else None,
            deleted_at=to_timestamp(self.deleted_at) if self.deleted_at else None,
            algorithms=[algo.to_proto() for algo in self.algorithms],
        )


class Algorithm(db.Model, SoftDeleteModel, ReviewTicketModel):
    __tablename__ = 'algorithms_v2'
    __table_args__ = (Index('idx_name',
                            'name'), UniqueConstraint('source', 'name', 'version', name='uniq_source_name_version'),
                      UniqueConstraint('uuid', name='uniq_uuid'), default_table_args('algorithms'))
    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)
    uuid = db.Column(db.String(64), comment='uuid')
    name = db.Column(db.String(255), comment='name')
    project_id = db.Column(db.Integer, comment='project id')
    version = db.Column(db.Integer, comment='version')
    type = db.Column('algorithm_type',
                     db.Enum(AlgorithmType, native_enum=False, length=32, create_constraint=False),
                     default=AlgorithmType.UNSPECIFIED,
                     key='type',
                     comment='algorithm type')
    source = db.Column(db.Enum(Source, native_enum=False, length=32, create_constraint=False),
                       default=Source.UNSPECIFIED,
                       comment='source')
    publish_status = db.Column(db.Enum(PublishStatus, native_enum=False, length=32, create_constraint=False),
                               default=PublishStatus.UNPUBLISHED,
                               comment='publish status')
    algorithm_project_id = db.Column(db.Integer, comment='algorithm project id')
    username = db.Column(db.String(255), comment='creator name')
    participant_id = db.Column(db.Integer, comment='participant id')
    path = db.Column('fspath', db.String(512), key='path', comment='algorithm path')
    parameter = db.Column(db.Text(), comment='parameter')
    favorite = db.Column(db.Boolean, default=False, comment='favorite')
    comment = db.Column('cmt', db.String(255), key='comment', comment='comment')
    created_at = db.Column(db.DateTime(timezone=True), default=now, comment='created time')
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now, comment='updated time')
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted time')
    project = db.relationship(Project.__name__, primaryjoin='foreign(Algorithm.project_id) == Project.id')
    user = db.relationship(User.__name__, primaryjoin='foreign(Algorithm.username) == User.username')
    participant = db.relationship(Participant.__name__,
                                  primaryjoin='foreign(Algorithm.participant_id) == Participant.id')
    algorithm_project = db.relationship(AlgorithmProject.__name__,
                                        primaryjoin='foreign(Algorithm.algorithm_project_id) == AlgorithmProject.id')

    def set_parameter(self, parameter: Optional[AlgorithmParameter] = None):
        if parameter is None:
            parameter = AlgorithmParameter()
        self.parameter = text_format.MessageToString(parameter)

    def get_parameter(self) -> Optional[AlgorithmParameter]:
        if self.parameter is not None:
            return text_format.Parse(self.parameter, AlgorithmParameter())
        return None

    def is_path_accessible(self, path: str):
        if self.path is None:
            return False
        return normalize_path(path).startswith(self.path)

    def get_participant_name(self):
        if self.participant is not None:
            return self.participant.name
        return None

    def get_status(self) -> AlgorithmStatus:
        if self.publish_status == PublishStatus.PUBLISHED:
            return AlgorithmStatus.PUBLISHED
        if self.ticket_uuid is not None:
            if self.ticket_status == TicketStatus.PENDING:
                return AlgorithmStatus.PENDING_APPROVAL
            if self.ticket_status == TicketStatus.APPROVED:
                return AlgorithmStatus.APPROVED
            if self.ticket_status == TicketStatus.DECLINED:
                return AlgorithmStatus.DECLINED
        return AlgorithmStatus.UNPUBLISHED

    def get_algorithm_project_uuid(self) -> Optional[str]:
        if self.algorithm_project:
            return self.algorithm_project.uuid
        return None

    def to_proto(self) -> AlgorithmPb:
        return AlgorithmPb(
            id=self.id,
            uuid=self.uuid,
            name=self.name,
            project_id=self.project_id,
            version=self.version,
            type=self.type.name,
            source=self.source.name,
            status=self.get_status().name,
            algorithm_project_id=self.algorithm_project_id,
            algorithm_project_uuid=self.get_algorithm_project_uuid(),
            username=self.username,
            participant_id=self.participant_id,
            participant_name=self.get_participant_name(),
            # TODO(gezhengqiang): delete participant name
            path=self.path,
            parameter=self.get_parameter(),
            favorite=self.favorite,
            comment=self.comment,
            created_at=to_timestamp(self.created_at) if self.created_at else None,
            updated_at=to_timestamp(self.updated_at) if self.updated_at else None,
            deleted_at=to_timestamp(self.deleted_at) if self.deleted_at else None,
        )


class PendingAlgorithm(db.Model, SoftDeleteModel):
    __tablename__ = 'pending_algorithms_v2'
    __table_args__ = (default_table_args('pending_algorithms'))
    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)
    algorithm_uuid = db.Column(db.String(64), comment='algorithm uuid')
    algorithm_project_uuid = db.Column(db.String(64), comment='algorithm project uuid')
    name = db.Column(db.String(255), comment='name')
    project_id = db.Column(db.Integer, comment='project id')
    version = db.Column(db.Integer, comment='version')
    type = db.Column('algorithm_type',
                     db.Enum(AlgorithmType, native_enum=False, length=32, create_constraint=False),
                     default=AlgorithmType.UNSPECIFIED,
                     key='type',
                     comment='algorithm type')
    participant_id = db.Column(db.Integer, comment='participant id')
    path = db.Column('fspath', db.String(512), key='path', comment='algorithm path')
    parameter = db.Column(db.Text(), comment='parameter')
    comment = db.Column('cmt', db.String(255), key='comment', comment='comment')
    created_at = db.Column(db.DateTime(timezone=True), default=now, comment='created time')
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now, comment='updated time')
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted time')
    project = db.relationship(Project.__name__, primaryjoin='foreign(PendingAlgorithm.project_id) == Project.id')
    participant = db.relationship(Participant.__name__,
                                  primaryjoin='foreign(PendingAlgorithm.participant_id) == Participant.id')
    algorithm_project = db.relationship(
        AlgorithmProject.__name__,
        primaryjoin='foreign(PendingAlgorithm.algorithm_project_uuid) == AlgorithmProject.uuid')

    def set_parameter(self, parameter: Optional[AlgorithmParameter] = None):
        if parameter is None:
            parameter = AlgorithmParameter()
        self.parameter = text_format.MessageToString(parameter)

    def get_parameter(self) -> Optional[AlgorithmParameter]:
        if self.parameter is not None:
            return text_format.Parse(self.parameter, AlgorithmParameter())
        return None

    def is_path_accessible(self, path: str):
        if self.path is None:
            return False
        return normalize_path(path).startswith(self.path)

    def get_participant_name(self):
        if self.participant:
            return self.participant.name
        return None

    def get_algorithm_project_id(self) -> Optional[int]:
        if self.algorithm_project:
            return self.algorithm_project.id
        return None

    def to_proto(self) -> PendingAlgorithmPb:
        return PendingAlgorithmPb(
            id=self.id,
            algorithm_uuid=self.algorithm_uuid,
            algorithm_project_uuid=self.algorithm_project_uuid,
            name=self.name,
            project_id=self.project_id,
            version=self.version,
            type=self.type.name,
            participant_id=self.participant_id,
            participant_name=self.get_participant_name(),
            path=self.path,
            parameter=self.get_parameter(),
            comment=self.comment,
            created_at=to_timestamp(self.created_at) if self.created_at else None,
            updated_at=to_timestamp(self.updated_at) if self.updated_at else None,
            deleted_at=to_timestamp(self.deleted_at) if self.deleted_at else None,
            algorithm_project_id=self.get_algorithm_project_id(),
        )

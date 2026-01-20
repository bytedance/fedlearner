# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import enum
from typing import Optional, List, Tuple

from google.protobuf import text_format
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Index, UniqueConstraint

from fedlearner_webconsole.proto.project_pb2 import ProjectRef, ParticipantsInfo, ProjectConfig, ParticipantInfo
from fedlearner_webconsole.utils.base_model.review_ticket_model import ReviewTicketModel
from fedlearner_webconsole.utils.base_model.softdelete_model import SoftDeleteModel
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.proto import project_pb2
from fedlearner_webconsole.participant.models import ParticipantType


class PendingProjectState(enum.Enum):
    PENDING = 'PENDING'
    ACCEPTED = 'ACCEPTED'
    FAILED = 'FAILED'
    CLOSED = 'CLOSED'


class ProjectRole(enum.Enum):
    COORDINATOR = 'COORDINATOR'
    PARTICIPANT = 'PARTICIPANT'


class Action(enum.Enum):
    ID_ALIGNMENT = 'ID_ALIGNMENT'
    DATA_ALIGNMENT = 'DATA_ALIGNMENT'
    HORIZONTAL_TRAIN = 'HORIZONTAL_TRAIN'
    VERTICAL_TRAIN = 'VERTICAL_TRAIN'
    VERTICAL_EVAL = 'VERTICAL_EVAL'
    VERTICAL_PRED = 'VERTICAL_PRED'
    VERTICAL_SERVING = 'VERTICAL_SERVING'
    WORKFLOW = 'WORKFLOW'
    TEE_SERVICE = 'TEE_SERVICE'
    TEE_RESULT_EXPORT = 'TEE_SERVICE'


class Project(db.Model):
    __tablename__ = 'projects_v2'
    __table_args__ = (UniqueConstraint('name', name='idx_name'), Index('idx_token', 'token'), {
        'comment': 'webconsole projects',
        'mysql_engine': 'innodb',
        'mysql_charset': 'utf8mb4',
    })
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id')
    role = db.Column(db.Enum(ProjectRole, length=32, native_enum=False, create_constraint=False),
                     default=ProjectRole.PARTICIPANT,
                     comment='pending project role')
    participants_info = db.Column(db.Text(), comment='participants info')

    name = db.Column(db.String(255), comment='name')
    token = db.Column(db.String(64), comment='token')
    config = db.Column(db.LargeBinary(), comment='config')
    comment = db.Column('cmt', db.Text(), key='comment', comment='comment')
    creator = db.Column(db.String(255), comment='creator')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           onupdate=func.now(),
                           server_default=func.now(),
                           comment='updated at')
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted at')
    participants = db.relationship('Participant',
                                   secondary='projects_participants_v2',
                                   primaryjoin='Project.id == foreign(ProjectParticipant.project_id)',
                                   secondaryjoin='Participant.id == foreign(ProjectParticipant.participant_id)')

    def set_config(self, proto: project_pb2.ProjectConfig):
        self.config = proto.SerializeToString()

    def _get_config(self) -> project_pb2.ProjectConfig:
        config = project_pb2.ProjectConfig()
        if self.config:
            config.ParseFromString(self.config)
        return config

    def get_variables(self) -> List[Variable]:
        return list(self._get_config().variables)

    def set_variables(self, variables: List[Variable]):
        config = self._get_config()
        del config.variables[:]
        config.variables.extend(variables)
        self.set_config(config)

    def get_storage_root_path(self, dft_value: str) -> str:
        variables = self.get_variables()
        for variable in variables:
            if variable.name == 'storage_root_path':
                return variable.value
        return dft_value

    def get_participant_type(self) -> Optional[ParticipantType]:
        if len(self.participants) == 0:
            return None
        return self.participants[0].get_type()

    def set_participants_info(self, proto: ParticipantsInfo):
        self.participants_info = text_format.MessageToString(proto)

    def get_participants_info(self) -> ParticipantsInfo:
        if self.participants_info is not None:
            return text_format.Parse(self.participants_info, ParticipantsInfo())
        return ParticipantsInfo()

    def to_ref(self) -> ProjectRef:
        participant_type = self.get_participant_type()
        ref = ProjectRef(id=self.id,
                         name=self.name,
                         creator=self.creator,
                         created_at=to_timestamp(self.created_at),
                         participant_type=participant_type.name if participant_type else None,
                         participants_info=self.get_participants_info(),
                         role=self.role.name if self.role else None)
        for participant in self.participants:
            ref.participants.append(participant.to_proto())
        return ref

    def to_proto(self) -> project_pb2.Project:
        participant_type = self.get_participant_type()
        proto = project_pb2.Project(id=self.id,
                                    name=self.name,
                                    creator=self.creator,
                                    created_at=to_timestamp(self.created_at),
                                    updated_at=to_timestamp(self.updated_at),
                                    participant_type=participant_type.name if participant_type else None,
                                    token=self.token,
                                    comment=self.comment,
                                    variables=self.get_variables(),
                                    participants_info=self.get_participants_info(),
                                    config=self._get_config(),
                                    role=self.role.name if self.role else None)
        for participant in self.participants:
            proto.participants.append(participant.to_proto())
        return proto


class PendingProject(db.Model, SoftDeleteModel, ReviewTicketModel):
    __tablename__ = 'pending_projects_v2'
    __table_args__ = (default_table_args('This is webconsole pending_project table'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id')
    name = db.Column(db.String(255), comment='name')
    uuid = db.Column(db.String(64), comment='uuid')
    config = db.Column(db.Text(), comment='config')
    state = db.Column(db.Enum(PendingProjectState, length=32, native_enum=False, create_constraint=False),
                      nullable=False,
                      default=PendingProjectState.PENDING,
                      comment='pending project stage state')
    participants_info = db.Column(db.Text(), comment='participants info')
    role = db.Column(db.Enum(ProjectRole, length=32, native_enum=False, create_constraint=False),
                     nullable=False,
                     default=ProjectRole.PARTICIPANT,
                     comment='pending project role')

    comment = db.Column('cmt', db.Text(), key='comment', comment='comment')
    creator_username = db.Column(db.String(255), comment='creator')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           onupdate=func.now(),
                           server_default=func.now(),
                           comment='updated at')

    def set_participants_info(self, proto: ParticipantsInfo):
        self.participants_info = text_format.MessageToString(proto)

    def get_participants_info(self) -> ParticipantsInfo:
        if self.participants_info is not None:
            return text_format.Parse(self.participants_info, ParticipantsInfo())
        return ParticipantsInfo()

    def set_config(self, proto: ProjectConfig):
        self.config = text_format.MessageToString(proto)

    def get_config(self) -> ProjectConfig:
        if self.config is not None:
            return text_format.Parse(self.config, ProjectConfig())
        return ProjectConfig()

    def to_proto(self) -> project_pb2.PendingProjectPb:
        return project_pb2.PendingProjectPb(id=self.id,
                                            name=self.name,
                                            uuid=self.uuid,
                                            config=self.get_config(),
                                            state=self.state.name,
                                            participants_info=self.get_participants_info(),
                                            role=self.role.name,
                                            comment=self.comment,
                                            creator_username=self.creator_username,
                                            created_at=to_timestamp(self.created_at),
                                            updated_at=to_timestamp(self.updated_at),
                                            ticket_uuid=self.ticket_uuid,
                                            ticket_status=self.ticket_status.name,
                                            participant_type=self.get_participant_type())

    def get_participant_info(self, pure_domain: str) -> Optional[ParticipantInfo]:
        return self.get_participants_info().participants_map.get(pure_domain)

    def get_coordinator_info(self) -> Tuple[str, ParticipantInfo]:
        for pure_domain, p_info in self.get_participants_info().participants_map.items():
            if p_info.role == ProjectRole.COORDINATOR.name:
                return pure_domain, p_info
        raise ValueError(f'not found coordinator in pending project {self.id}')

    def get_participant_type(self) -> str:
        # In the short term, the project will only have one type of participants,
        # make pending project type hack to be the type of the first participant.
        for info in self.get_participants_info().participants_map.values():
            if info.role == ProjectRole.PARTICIPANT.name:
                return info.type
        return ParticipantType.LIGHT_CLIENT.name

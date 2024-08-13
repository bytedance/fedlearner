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

# coding: utf-8
import json
from enum import Enum
from typing import Dict
from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.sql import func

from fedlearner_webconsole.proto import participant_pb2
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.utils.domain_name import get_pure_domain_name
from fedlearner_webconsole.utils.base_model.review_ticket_model import ReviewTicketModel


class ParticipantType(Enum):
    PLATFORM = 0
    LIGHT_CLIENT = 1


class Participant(db.Model, ReviewTicketModel):
    __tablename__ = 'participants_v2'
    __table_args__ = (UniqueConstraint('domain_name', name='uniq_domain_name'),
                      default_table_args('This is webconsole participant table.'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='participant id')
    name = db.Column(db.String(255), nullable=False, comment='participant name')
    domain_name = db.Column(db.String(255), unique=True, nullable=False, comment='participant domain_name')
    host = db.Column(db.String(255), comment='participant host')
    port = db.Column(db.Integer, comment='host port')
    type = db.Column('participant_type',
                     db.Enum(ParticipantType, native_enum=False, length=64, create_constraint=False),
                     default=ParticipantType.PLATFORM,
                     key='type',
                     comment='participant type')
    comment = db.Column('cmt', db.Text(), key='comment', comment='comment')
    extra = db.Column(db.Text(), comment='extra_info')
    last_connected_at = db.Column(db.DateTime(timezone=True), comment='last connected at')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           onupdate=func.now(),
                           server_default=func.now(),
                           comment='updated at')

    def set_extra_info(self, extra_info: Dict):
        self.extra = json.dumps(extra_info)

    def get_extra_info(self) -> Dict:
        if self.extra is not None:
            return json.loads(self.extra)
        return {}

    def get_type(self) -> ParticipantType:
        return self.type if self.type else ParticipantType.PLATFORM

    def pure_domain_name(self):
        return get_pure_domain_name(self.domain_name)

    def to_proto(self) -> participant_pb2.Participant:
        extra_info = self.get_extra_info()
        proto = participant_pb2.Participant(
            id=self.id,
            name=self.name,
            domain_name=self.domain_name,
            pure_domain_name=self.pure_domain_name(),
            host=self.host,
            port=self.port,
            type=self.get_type().name,
            comment=self.comment,
            last_connected_at=to_timestamp(self.last_connected_at) if self.last_connected_at else 0,
            created_at=to_timestamp(self.created_at),
            updated_at=to_timestamp(self.updated_at) if self.updated_at else 0,
            extra=participant_pb2.ParticipantExtra(is_manual_configured=extra_info.get('is_manual_configured', False)))
        return proto


class ProjectParticipant(db.Model):
    __tablename__ = 'projects_participants_v2'
    __table_args__ = (Index('idx_project_id', 'project_id'), Index('idx_participant_id', 'participant_id'),
                      default_table_args('This is webcocsole projects and participants relationship table.'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='relationship id')
    project_id = db.Column(db.Integer, nullable=False, comment='project_id id')
    participant_id = db.Column(db.Integer, nullable=False, comment='participants_id id')

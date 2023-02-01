#  Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  coding: utf-8
from uuid import uuid4
import enum

from sqlalchemy import UniqueConstraint, func
from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.utils.mixins import to_dict_mixin
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.proto.auth_pb2 import User
from fedlearner_webconsole.utils.pp_datetime import to_timestamp


class EventType(enum.Enum):
    # USER_ENDPOINT maps to events with source of 'API/UI'
    USER_ENDPOINT = 0
    # RPC maps to events with source of 'RPC'
    RPC = 1


@to_dict_mixin(ignores=['updated_at', 'deleted_at', 'user_id'],
               extras={
                   'user': lambda e: {
                       'id': e.user.id,
                       'username': e.user.username,
                       'role': e.user.role.name,
                   },
               })
class EventModel(db.Model):
    __tablename__ = 'events_v2'
    __table_args__ = (UniqueConstraint('uuid', name='uniq_uuid'), default_table_args('webconsole audit events'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='auto-incremented id')
    uuid = db.Column(db.String(255), nullable=False, comment='UUID of the event', default=lambda _: str(uuid4()))
    name = db.Column(db.String(255), nullable=False, comment='the name of the event')
    user_id = db.Column(db.Integer, comment='the ID of the user who triggered the event')
    resource_type = db.Column(db.Enum(*Event.ResourceType.keys(),
                                      native_enum=False,
                                      create_constraint=False,
                                      length=32,
                                      name='resource_type'),
                              nullable=False,
                              comment='the type of the resource')
    resource_name = db.Column(db.String(512), nullable=False, comment='the name of the resource')
    op_type = db.Column(db.Enum(*Event.OperationType.keys(),
                                native_enum=False,
                                create_constraint=False,
                                length=32,
                                name='op_type'),
                        nullable=False,
                        comment='the type of the operation of the event')
    # Due to compatibility, audit API double writes result and result_code field
    # TODO(yeqiuhan): remove result field
    result = db.Column(db.Enum(*Event.Result.keys(),
                               native_enum=False,
                               create_constraint=False,
                               length=32,
                               name='result'),
                       nullable=False,
                       comment='the result of the operation')
    result_code = db.Column(db.String(255), comment='the result code of the operation')
    source = db.Column(db.Enum(*Event.Source.keys(),
                               native_enum=False,
                               create_constraint=False,
                               length=32,
                               name='source'),
                       nullable=False,
                       comment='the source that triggered the event')
    coordinator_pure_domain_name = db.Column(db.String(255), comment='name of the coordinator')
    project_id = db.Column(db.Integer, comment='project_id corresponds to participants name')
    extra = db.Column(db.Text, comment='extra info in JSON')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           onupdate=func.now(),
                           server_default=func.now(),
                           comment='updated at')
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted at')
    user = db.relationship('User', primaryjoin='foreign(EventModel.user_id) == User.id')

    def to_proto(self) -> Event:
        return Event(user_id=self.user_id,
                     resource_type=Event.ResourceType.Value(self.resource_type),
                     resource_name=self.resource_name,
                     op_type=Event.OperationType.Value(self.op_type),
                     result=Event.Result.Value(self.result),
                     result_code=self.result_code,
                     source=Event.Source.Value(self.source),
                     name=self.name,
                     coordinator_pure_domain_name=self.coordinator_pure_domain_name,
                     project_id=self.project_id,
                     extra=self.extra,
                     user=User(id=self.user.id, username=self.user.username, role=self.user.role.value)
                     if self.user is not None else None,
                     event_id=self.id,
                     uuid=self.uuid,
                     created_at=to_timestamp(self.created_at))


def to_model(proto: Event) -> EventModel:
    return EventModel(name=proto.name,
                      user_id=proto.user_id,
                      resource_type=Event.ResourceType.Name(proto.resource_type),
                      resource_name=proto.resource_name,
                      op_type=Event.OperationType.Name(proto.op_type),
                      coordinator_pure_domain_name=proto.coordinator_pure_domain_name,
                      result=Event.Result.Name(proto.result),
                      result_code=proto.result_code,
                      source=Event.Source.Name(proto.source),
                      extra=proto.extra,
                      project_id=proto.project_id)

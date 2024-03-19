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
from abc import ABCMeta, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, Query
from sqlalchemy.sql.schema import Column

from envs import Envs
from fedlearner_webconsole.audit.models import EventModel, to_model
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterOp, SimpleExpression
from fedlearner_webconsole.utils.filtering import FieldType, FilterBuilder, SupportedField
from fedlearner_webconsole.auth.services import UserService
from fedlearner_webconsole.db import db


def _contains_case_insensitive(exp: SimpleExpression):
    c: Column = getattr(EventModel, exp.field)
    return c.ilike(f'%{exp.string_value}%')


def _equals_username(exp: SimpleExpression):
    username = exp.string_value
    c: Column = EventModel.user_id
    with db.session_scope() as session:
        user = UserService(session).get_user_by_username(username)
        if user is None:
            return False
    return c == user.id


def _later(exp: SimpleExpression):
    c: Column = EventModel.created_at
    dt = datetime.fromtimestamp(exp.number_value, tz=timezone.utc)
    return c > dt


def _earlier(exp: SimpleExpression):
    c: Column = EventModel.created_at
    dt = datetime.fromtimestamp(exp.number_value, tz=timezone.utc)
    return c < dt


class IStorage(metaclass=ABCMeta):

    @abstractmethod
    def save_event(self, event: Event) -> None:
        """Save the event instance into corresponding storage.

        Args:
            event (Event): The event instance waited to be stored.
        """

    @abstractmethod
    def get_events(self, filter_exp: Optional[FilterExpression] = None) -> Query:
        """Get event records from corresponding storage.

        Args:
            filter_exp (FilterExpression): Filtering expression defined in utils/filtering.py
        Returns:
            A Query object contains selected events.
        """

    @abstractmethod
    def delete_events(self, filter_exp: FilterExpression) -> None:
        """Delete event records for a period of time.

        Args:
            filter_exp (FilterExpression): Filtering expression defined in utils/filtering.py
        """


class MySqlStorage(IStorage):

    FILTER_FIELDS = {
        'name':
            SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: _contains_case_insensitive}),
        'username':
            SupportedField(type=FieldType.STRING, ops={FilterOp.EQUAL: _equals_username}),
        'resource_type':
            SupportedField(type=FieldType.STRING, ops={
                FilterOp.CONTAIN: _contains_case_insensitive,
                FilterOp.IN: None
            }),
        'resource_name':
            SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: _contains_case_insensitive}),
        'op_type':
            SupportedField(type=FieldType.STRING, ops={
                FilterOp.EQUAL: None,
                FilterOp.IN: None
            }),
        'coordinator_pure_domain_name':
            SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: _contains_case_insensitive}),
        'project_id':
            SupportedField(type=FieldType.NUMBER, ops={FilterOp.EQUAL: None}),
        'result':
            SupportedField(type=FieldType.STRING, ops={FilterOp.EQUAL: None}),
        'result_code':
            SupportedField(type=FieldType.STRING, ops={FilterOp.EQUAL: None}),
        'source':
            SupportedField(type=FieldType.STRING, ops={
                FilterOp.EQUAL: None,
                FilterOp.IN: None
            }),
        'start_time':
            SupportedField(type=FieldType.NUMBER, ops={FilterOp.GREATER_THAN: _later}),
        'end_time':
            SupportedField(type=FieldType.NUMBER, ops={FilterOp.LESS_THAN: _earlier}),
    }

    def __init__(self, session: Session):
        self._session = session
        self._filter_builder = FilterBuilder(model_class=EventModel, supported_fields=self.FILTER_FIELDS)

    def save_event(self, event: Event) -> None:
        self._session.add(to_model(event))

    def get_events(self, filter_exp: Optional[FilterExpression] = None) -> Query:
        events = self._session.query(EventModel).filter(EventModel.deleted_at.is_(None))
        if filter_exp is not None:
            events = self._filter_builder.build_query(events, filter_exp)
        return events.order_by(EventModel.id.desc())

    def delete_events(self, filter_exp: FilterExpression) -> None:
        events = self._session.query(EventModel).filter(EventModel.deleted_at.is_(None))
        events = self._filter_builder.build_query(events, filter_exp)
        events.update({'deleted_at': func.now()}, synchronize_session='fetch')


def get_storage(session: Session) -> Optional[IStorage]:
    """Get a storage object accordingly.

    Args:
        session (Session): Session used to query records.

    Returns:
        A IStorage object that can save, get and delete events.
    """
    if Envs.AUDIT_STORAGE == 'db':
        return MySqlStorage(session)
    # TODO(wangsen.0914): add CloudStorage or other types of storages later
    return None

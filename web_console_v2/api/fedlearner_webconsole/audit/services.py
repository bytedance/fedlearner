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
from typing import Optional

from sqlalchemy.orm import Session, Query

from fedlearner_webconsole.audit.storage import get_storage
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression


class EventService:

    def __init__(self, session: Session):
        """Construct a EventService.

        Args:
            session (Session): SQLAlchemy session.
        """
        self._session = session
        self.storage = get_storage(self._session)

    def emit_event(self, event: Event) -> None:
        """Pass a Event instance to storage.

        Args:
            event (Event): Records to store.

        Raises:
            ValueError: Fields are invalid.
        """
        self.storage.save_event(event)

    def get_events(self, filter_exp: Optional[FilterExpression] = None) -> Query:
        """Get events by time and additional conditions in {event}.

        Args:
            filter_exp (FilterExpression): Filtering expression defined in utils/filtering.py
        Returns:
            A SQLAlchemy Query object contains selected records.
        """
        return self.storage.get_events(filter_exp)

    def delete_events(self, filter_exp: FilterExpression):
        """Delete events by time.

        Args:
            filter_exp (FilterExpression): Filtering expression defined in utils/filtering.py
        """
        self.storage.delete_events(filter_exp)

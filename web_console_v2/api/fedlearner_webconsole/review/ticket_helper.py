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

from abc import ABC, abstractmethod
import json
from typing import Callable
from sqlalchemy.orm import Session

from fedlearner_webconsole.flag.models import Flag
from fedlearner_webconsole.review import common
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.proto import review_pb2
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.rpc.v2.review_service_client import ReviewServiceClient
from fedlearner_webconsole.utils.flask_utils import get_current_user


class ITicketHelper(ABC):

    @abstractmethod
    def create_ticket(self, ticket_type: review_pb2.TicketType, details: review_pb2.TicketDetails) -> review_pb2.Ticket:
        raise NotImplementedError()

    @abstractmethod
    def get_ticket(self, uuid: str) -> review_pb2.Ticket:
        raise NotImplementedError()

    @abstractmethod
    def validate_ticket(self, uuid: str, validate_fn: Callable[[review_pb2.Ticket], bool]) -> bool:
        raise NotImplementedError()


def _get_model_from_ticket_type(ticket_type: review_pb2.TicketType) -> db.Model:
    model = common.REVIEW_ORM_MAPPER.get(ticket_type)
    if model is None:
        raise InvalidArgumentException(details=f'failed to get orm.Model for {review_pb2.TicketType.Name(ticket_type)}')
    return model


class NoCenterServerTicketHelper(ITicketHelper):

    def __init__(self, session: Session):
        self._session = session

    def create_ticket(self, ticket_type: review_pb2.TicketType, details: review_pb2.TicketDetails) -> review_pb2.Ticket:
        model = _get_model_from_ticket_type(ticket_type)
        # TODO(wangsen.0914): add extension for filter related resources other than uuid.
        resource = self._session.query(model).filter_by(uuid=details.uuid).first()
        if resource is None:
            raise InvalidArgumentException(details=f'failed to get resource with {details.uuid}')
        resource.ticket_status = TicketStatus(review_pb2.ReviewStatus.Name(review_pb2.ReviewStatus.APPROVED))
        resource.ticket_uuid = common.NO_CENTRAL_SERVER_UUID
        return review_pb2.Ticket(type=ticket_type,
                                 details=details,
                                 uuid=common.NO_CENTRAL_SERVER_UUID,
                                 status=review_pb2.ReviewStatus.APPROVED,
                                 review_strategy=review_pb2.ReviewStrategy.AUTO)

    def get_ticket(self, uuid: str) -> review_pb2.Ticket:
        return review_pb2.Ticket(uuid=uuid,
                                 type=review_pb2.TicketType.UNKOWN_TYPE,
                                 status=review_pb2.ReviewStatus.APPROVED,
                                 review_strategy=review_pb2.ReviewStrategy.AUTO)

    def validate_ticket(self, uuid: str, validate_fn: Callable[[review_pb2.Ticket], bool]) -> bool:
        del validate_fn  # ignore validate_fn, because center server is not configured.

        if uuid != common.NO_CENTRAL_SERVER_UUID:
            return False
        return True


class CenterServerTicketHelper(ITicketHelper):

    def __init__(self, session: Session, domain_name: str):
        self._session = session
        self._domain_name = domain_name

    def create_ticket(self, ticket_type: review_pb2.TicketType, details: review_pb2.TicketDetails) -> review_pb2.Ticket:
        model = _get_model_from_ticket_type(ticket_type)
        # TODO(wangsen.0914): add extension for filter related resources other than uuid.
        resource = self._session.query(model).filter_by(uuid=details.uuid).first()
        if resource is None:
            raise InvalidArgumentException(details=f'failed to get resource with {details.uuid}')
        client = ReviewServiceClient.from_participant(domain_name=self._domain_name)
        current_user = get_current_user()
        creator_username = current_user.username if current_user else None
        ticket = client.create_ticket(ticket_type, creator_username, details)
        resource.ticket_status = TicketStatus(review_pb2.ReviewStatus.Name(ticket.status))
        resource.ticket_uuid = ticket.uuid
        return ticket

    def get_ticket(self, uuid: str) -> review_pb2.Ticket:
        client = ReviewServiceClient.from_participant(domain_name=self._domain_name)
        return client.get_ticket(uuid)

    def validate_ticket(self, uuid: str, validate_fn: Callable[[review_pb2.Ticket], bool]) -> bool:
        ticket = self.get_ticket(uuid)
        if ticket.uuid != uuid:
            return False
        return validate_fn(ticket)


def get_ticket_helper(session: Session) -> ITicketHelper:
    configuration = json.loads(Flag.REVIEW_CENTER_CONFIGURATION.value)
    if not configuration:
        return NoCenterServerTicketHelper(session)
    domain_name = configuration['domain_name']
    return CenterServerTicketHelper(session, domain_name)

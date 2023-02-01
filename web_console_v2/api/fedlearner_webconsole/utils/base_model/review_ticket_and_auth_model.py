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
import sqlalchemy as sa
from google.protobuf import text_format

from fedlearner_webconsole.utils.base_model.auth_model import AuthModel, AuthStatus
from fedlearner_webconsole.utils.base_model.review_ticket_model import ReviewTicketModel, TicketStatus
from fedlearner_webconsole.proto import project_pb2


class AuthFrontendState(enum.Enum):
    TICKET_PENDING = 'TICKET_PENDING'
    TICKET_DECLINED = 'TICKET_DECLINED'
    AUTH_PENDING = 'AUTH_PENDING'
    AUTH_APPROVED = 'AUTH_APPROVED'


class ReviewTicketAndAuthModel(AuthModel, ReviewTicketModel):

    participants_info = sa.Column(sa.Text(), comment='participants info')

    @property
    def auth_frontend_state(self) -> AuthFrontendState:
        if self.ticket_status == TicketStatus.PENDING:
            return AuthFrontendState.TICKET_PENDING
        if self.ticket_status == TicketStatus.DECLINED:
            return AuthFrontendState.TICKET_DECLINED
        if self.ticket_status == TicketStatus.APPROVED and self.is_all_participants_authorized():
            return AuthFrontendState.AUTH_APPROVED
        return AuthFrontendState.AUTH_PENDING

    def set_participants_info(self, participants_info: project_pb2.ParticipantsInfo):
        self.participants_info = text_format.MessageToString(participants_info)

    def get_participants_info(self) -> project_pb2.ParticipantsInfo:
        participants_info = project_pb2.ParticipantsInfo()
        if self.participants_info is not None:
            participants_info = text_format.Parse(self.participants_info, project_pb2.ParticipantsInfo())
        return participants_info

    def is_all_participants_authorized(self) -> bool:
        participants_info_list = self.get_participants_info().participants_map.values()
        return all(
            participant_info.auth_status == AuthStatus.AUTHORIZED.name for participant_info in participants_info_list)

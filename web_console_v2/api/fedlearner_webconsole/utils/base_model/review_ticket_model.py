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


class TicketStatus(enum.Enum):
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    DECLINED = 'DECLINED'


class ReviewTicketModel(object):

    ticket_uuid = sa.Column(sa.String(255),
                            nullable=True,
                            comment='review ticket uuid, empty if review function is disable')
    ticket_status = sa.Column(sa.Enum(TicketStatus, length=32, native_enum=False, create_constraint=False),
                              default=TicketStatus.APPROVED,
                              server_default=TicketStatus.APPROVED.name,
                              comment='review ticket status')

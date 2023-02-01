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

import logging
from typing import Tuple
from fedlearner_webconsole.db import db

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.interface import IRunnerV2
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.review.common import REVIEW_ORM_MAPPER
from fedlearner_webconsole.rpc.v2.review_service_client import ReviewServiceClient
from fedlearner_webconsole.proto import review_pb2
from fedlearner_webconsole.proto.composer_pb2 import RunnerOutput, TicketHelperOutput
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus


class TicketHelperRunner(IRunnerV2):

    def __init__(self, domain_name: str):
        self._domain_name = domain_name

    def _update_ticket_status(self, resource) -> bool:
        uuid = getattr(resource, 'ticket_uuid')
        client = ReviewServiceClient.from_participant(domain_name=self._domain_name)
        resp = client.get_ticket(uuid)
        status = TicketStatus(review_pb2.ReviewStatus.Name(resp.status))
        if status in [TicketStatus.APPROVED, TicketStatus.DECLINED]:
            setattr(resource, 'ticket_status', status)
            return True

        return False

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        del context

        ticket_output = TicketHelperOutput()
        for ttype, orm in REVIEW_ORM_MAPPER.items():
            ttype_name = review_pb2.TicketType.Name(ttype)
            updated_ticket = ticket_output.updated_ticket[ttype_name].ids
            unupdated_ticket = ticket_output.unupdated_ticket[ttype_name].ids
            failed_ticket = ticket_output.failed_ticket[ttype_name].ids
            with db.session_scope() as session:
                resources = session.query(orm).filter_by(ticket_status=TicketStatus.PENDING).all()
                for resource in resources:
                    try:
                        if self._update_ticket_status(resource):
                            updated_ticket.append(resource.id)
                        else:
                            unupdated_ticket.append(resource.id)
                    except Exception:  # pylint: disable=broad-except
                        failed_ticket.append(resource.id)
                session.commit()
            logging.info(f'ticket routine for {ttype_name}:')
            logging.info(f' updated_ticket {updated_ticket}')
            logging.info(f' failed_ticket {failed_ticket}')

        return (RunnerStatus.DONE, RunnerOutput(ticket_helper_output=ticket_output))

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
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fedlearner_webconsole.exceptions import InvalidArgumentException, NotFoundException
from fedlearner_webconsole.cleanup.models import Cleanup, CleanupState
from fedlearner_webconsole.proto.cleanup_pb2 import CleanupParameter, CleanupPb
from fedlearner_webconsole.proto.filtering_pb2 import FilterOp, FilterExpression
from fedlearner_webconsole.utils.paginate import Pagination, paginate
from fedlearner_webconsole.utils.filtering import SupportedField, FieldType, FilterBuilder


class CleanupService():

    FILTER_FIELDS = {
        'state': SupportedField(type=FieldType.STRING, ops={FilterOp.EQUAL: None}),
        'resource_type': SupportedField(type=FieldType.STRING, ops={FilterOp.EQUAL: None}),
        'resource_id': SupportedField(type=FieldType.NUMBER, ops={FilterOp.EQUAL: None}),
    }

    def __init__(self, session: Session):
        self._session = session
        self._filter_builder = FilterBuilder(model_class=Cleanup, supported_fields=self.FILTER_FIELDS)

    def get_cleanups(self,
                     page: Optional[int] = None,
                     page_size: Optional[int] = None,
                     filter_exp: Optional[FilterExpression] = None) -> Pagination:
        query = self._session.query(Cleanup)
        if filter_exp:
            query = self._filter_builder.build_query(query, filter_exp)
        query = query.order_by(Cleanup.created_at.desc())
        return paginate(query, page, page_size)

    def get_cleanup(self, cleanup_id: int = 0) -> CleanupPb:
        cleanup = self._session.query(Cleanup).get(cleanup_id)
        if not cleanup:
            raise NotFoundException(f'Failed to find cleanup: {cleanup_id}')
        return cleanup.to_proto()

    def create_cleanup(self, cleanup_parmeter: CleanupParameter) -> Cleanup:
        cleanup = Cleanup(
            state=CleanupState.WAITING,
            resource_id=cleanup_parmeter.resource_id,
            resource_type=cleanup_parmeter.resource_type,
            target_start_at=datetime.fromtimestamp(cleanup_parmeter.target_start_at, tz=timezone.utc),
            payload=cleanup_parmeter.payload,
        )
        self._session.add(cleanup)
        return cleanup

    def _cancel_cleanup(self, cleanup: Cleanup) -> CleanupPb:
        if not cleanup.is_cancellable:
            error_msg = f'cleanup: {cleanup.id} can not be canceled'
            logging.error(error_msg)
            raise InvalidArgumentException(error_msg)
        cleanup.state = CleanupState.CANCELED
        return cleanup.to_proto()

    def cancel_cleanup_by_id(self, cleanup_id: int = 0) -> CleanupPb:
        # apply exclusive lock on cleanup to avoid race condition on updating its state
        cleanup = self._session.query(Cleanup).populate_existing().with_for_update().filter(
            Cleanup.id == cleanup_id).first()
        if not cleanup:
            error_msg = f'there is no cleanup with cleanup_id:{cleanup_id}'
            logging.error(error_msg)
            raise InvalidArgumentException(error_msg)
        return self._cancel_cleanup(cleanup)

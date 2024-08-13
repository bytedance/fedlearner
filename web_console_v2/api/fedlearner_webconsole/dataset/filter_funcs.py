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

from sqlalchemy import and_, or_

from fedlearner_webconsole.dataset.models import Dataset, DatasetFormat, PublishFrontendState
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.proto.filtering_pb2 import SimpleExpression


def dataset_format_filter_op_in(simple_exp: SimpleExpression):
    filter_list = []
    dataset_format_str_list = [dataset_format.name for dataset_format in DatasetFormat]
    for dataset_format in simple_exp.list_value.string_list:
        if dataset_format not in dataset_format_str_list:
            raise ValueError(f'dataset_format does not has type {dataset_format}')
        filter_list.append(DatasetFormat[dataset_format].value)
    return Dataset.dataset_format.in_(filter_list)


def dataset_format_filter_op_equal(simple_exp: SimpleExpression):
    for dataset_format in DatasetFormat:
        if simple_exp.string_value == dataset_format.name:
            return Dataset.dataset_format == dataset_format.value
    raise ValueError(f'dataset_format does not has type {simple_exp.string_value}')


def dataset_publish_frontend_filter_op_equal(simple_exp: SimpleExpression):
    if simple_exp.string_value == PublishFrontendState.PUBLISHED.name:
        return and_(Dataset.is_published.is_(True), Dataset.ticket_status == TicketStatus.APPROVED)
    if simple_exp.string_value == PublishFrontendState.TICKET_PENDING.name:
        return and_(Dataset.is_published.is_(True), Dataset.ticket_status == TicketStatus.PENDING)
    if simple_exp.string_value == PublishFrontendState.TICKET_DECLINED.name:
        return and_(Dataset.is_published.is_(True), Dataset.ticket_status == TicketStatus.DECLINED)
    return Dataset.is_published.is_(False)


def dataset_auth_status_filter_op_in(simple_exp: SimpleExpression):
    filter_list = [AuthStatus[auth_status] for auth_status in simple_exp.list_value.string_list]
    filter_exp = Dataset.auth_status.in_(filter_list)
    if AuthStatus.AUTHORIZED in filter_list:
        filter_exp = or_(Dataset.auth_status.is_(None), filter_exp)
    return filter_exp

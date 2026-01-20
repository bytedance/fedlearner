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
from string import Template
from typing import NamedTuple

from fedlearner_webconsole.proto.notification_pb2 import Notification


class NotificationTemplate(NamedTuple):
    subject: Template
    content: Template


class NotificationTemplateName(enum.Enum):
    WORKFLOW_COMPLETE = 'WORKFLOW_COMPLETE'


_UNKNOWN_TEMPLATE = NotificationTemplate(
    subject=Template('Unknown email'),
    content=Template(''),
)

_WORKFLOW_COMPLETE_TEMPLATE = NotificationTemplate(
    subject=Template('【隐私计算平台】工作流「${name}」- 运行结束 - ${state}'),
    content=Template('「工作流中心」：工作流「${name}」- 运行结束 - ${state}，详情请见：${link}'),
)

TEMPLATES = {NotificationTemplateName.WORKFLOW_COMPLETE: _WORKFLOW_COMPLETE_TEMPLATE}


def render(template_name: NotificationTemplateName, **kwargs) -> Notification:
    template = TEMPLATES.get(template_name, _UNKNOWN_TEMPLATE)
    return Notification(
        subject=template.subject.safe_substitute(kwargs),
        content=template.content.safe_substitute(kwargs),
    )

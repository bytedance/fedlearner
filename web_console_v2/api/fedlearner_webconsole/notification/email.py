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

from fedlearner_webconsole.notification.sender import send
from fedlearner_webconsole.notification.template import NotificationTemplateName, render


def send_email(address: str, template_name: NotificationTemplateName, **kwargs):
    notification = render(template_name, **kwargs)
    # TODO(linfan.fine): validate the email address
    if address:
        notification.receivers.append(address)
    send(notification)

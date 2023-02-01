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

import unittest
from unittest.mock import patch, Mock

from fedlearner_webconsole.notification.email import send_email
from fedlearner_webconsole.notification.template import NotificationTemplateName
from fedlearner_webconsole.proto.notification_pb2 import Notification


class EmailTest(unittest.TestCase):

    @patch('fedlearner_webconsole.notification.email.render')
    @patch('fedlearner_webconsole.notification.email.send')
    def test_send_email(self, mock_send: Mock, mock_render: Mock):
        subject = 'test_subject'
        content = 'test_content'
        address = 'a@b.com'
        mock_render.return_value = Notification(subject=subject, content=content)
        send_email(address, NotificationTemplateName.WORKFLOW_COMPLETE, var1='aaa', var2='bbb')
        mock_send.assert_called_once_with(Notification(subject=subject, content=content, receivers=[address]))
        mock_render.assert_called_once_with(NotificationTemplateName.WORKFLOW_COMPLETE, var1='aaa', var2='bbb')


if __name__ == '__main__':
    unittest.main()

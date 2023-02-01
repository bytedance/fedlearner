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
from unittest.mock import MagicMock

from fedlearner_webconsole.notification.sender import register_sender, send
from fedlearner_webconsole.proto.notification_pb2 import Notification


class SenderTest(unittest.TestCase):

    def test_send(self):
        mock_sender = MagicMock()
        mock_sender.send = MagicMock()
        register_sender('mock_sender', mock_sender)

        notification = Notification(subject='test subject', content='test content', receivers=[])
        send(notification)
        mock_sender.send.assert_called_once_with(notification)

    def test_send_with_no_sender(self):
        notification = Notification(subject='test subject', content='test content', receivers=[])
        # No exception is expected
        send(notification)


if __name__ == '__main__':
    unittest.main()

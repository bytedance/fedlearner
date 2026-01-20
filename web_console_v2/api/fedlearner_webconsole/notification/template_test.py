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

from fedlearner_webconsole.notification.template import render, NotificationTemplateName
from fedlearner_webconsole.proto.notification_pb2 import Notification


class TemplateTest(unittest.TestCase):

    def test_render(self):
        email = render(NotificationTemplateName.WORKFLOW_COMPLETE,
                       name='test workflow',
                       state='FAILED',
                       link='www.a.com')
        self.assertEqual(
            email,
            Notification(subject='【隐私计算平台】工作流「test workflow」- 运行结束 - FAILED',
                         content='「工作流中心」：工作流「test workflow」- 运行结束 - FAILED，详情请见：www.a.com'))
        # some variables are not passed
        email = render(NotificationTemplateName.WORKFLOW_COMPLETE, name='test workflow', unknown_var='123')
        self.assertEqual(
            email,
            Notification(subject='【隐私计算平台】工作流「test workflow」- 运行结束 - ${state}',
                         content='「工作流中心」：工作流「test workflow」- 运行结束 - ${state}，详情请见：${link}'))

    def test_render_unknown(self):
        self.assertEqual(render('unknown template', hello=123), Notification(subject='Unknown email',))


if __name__ == '__main__':
    unittest.main()

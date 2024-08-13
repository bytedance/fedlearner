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

from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.setting_pb2 import SettingPb
from fedlearner_webconsole.setting.models import Setting
from testing.no_web_server_test_case import NoWebServerTestCase


class SettingTest(NoWebServerTestCase):

    def test_to_proto(self):
        with db.session_scope() as session:
            setting = Setting(
                uniq_key='test',
                value='test value',
            )
            session.add(setting)
            session.commit()
        with db.session_scope() as session:
            setting = session.query(Setting).filter_by(uniq_key='test').first()
            self.assertEqual(setting.to_proto(), SettingPb(
                uniq_key='test',
                value='test value',
            ))


if __name__ == '__main__':
    unittest.main()

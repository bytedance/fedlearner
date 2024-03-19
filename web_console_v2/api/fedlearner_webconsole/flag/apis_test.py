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

#  coding: utf-8
from unittest.mock import patch
from testing.common import BaseTestCase
import unittest


class FlagsApisTest(BaseTestCase):

    @patch('fedlearner_webconsole.flag.apis.get_flags')
    def test_get_flags(self, get_flags):
        get_flags.return_value = {'first_flag': False, 'second_flag': 0}
        response = self.get_helper('/api/v2/flags')
        flags = self.get_response_data(response)

        self.assertEqual(False, flags.get('first_flag'))
        self.assertEqual(0, flags.get('second_flag'))


if __name__ == '__main__':
    unittest.main()

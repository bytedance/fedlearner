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
import unittest
from fedlearner_webconsole.flag.models import _Flag, get_flags


class FlagMock(object):
    FIRST_FLAG = _Flag('first_flag', False)
    SECOND_FLAG = _Flag('second_flag', 0)


MOCK_ENV_FLAGS = {'first_flag': True, 'second_flag': 1}


class FlagsModelsTest(unittest.TestCase):

    @patch('fedlearner_webconsole.flag.models._Flag.FLAGS_DICT', MOCK_ENV_FLAGS)
    def test_fallback(self):
        # this instance will be modified to True
        first_flag = _Flag('first_flag', False)

        # this instance will fallback to False due to type error
        second_flag = _Flag('second_flag', False)

        # this instance will fallback to 0 due to the absence of its value in envs
        third_flag = _Flag('third_flag', 0)

        self.assertEqual(True, first_flag.value)
        self.assertEqual(False, second_flag.value)
        self.assertEqual(0, third_flag.value)

    @patch('fedlearner_webconsole.flag.models.Flag', FlagMock)
    def test_get_flags(self):
        flags = get_flags()

        self.assertEqual(False, flags.get('first_flag'))
        self.assertEqual(0, flags.get('second_flag'))


if __name__ == '__main__':
    unittest.main()

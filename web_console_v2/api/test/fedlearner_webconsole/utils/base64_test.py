# Copyright 2021 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import unittest

from fedlearner_webconsole.utils.base64 import base64encode, base64decode


class Base64Test(unittest.TestCase):
    def test_base64encode(self):
        self.assertEqual(base64encode('hello 1@2'), 'aGVsbG8gMUAy')
        self.assertEqual(base64encode('😈'), '8J+YiA==')

    def test_base64decode(self):
        self.assertEqual(base64decode('aGVsbG8gMUAy'), 'hello 1@2')
        self.assertEqual(base64decode('JjEzOVlUKiYm'), '&139YT*&&')

    def test_base64_encode_and_decode(self):
        self.assertEqual(base64decode(base64encode('test')), 'test')
        self.assertEqual(base64encode(base64decode('aGVsbG8gMUAy')),
                         'aGVsbG8gMUAy')


if __name__ == '__main__':
    unittest.main()

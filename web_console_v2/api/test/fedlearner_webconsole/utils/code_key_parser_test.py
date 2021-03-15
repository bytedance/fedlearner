# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
from fedlearner_webconsole.utils.code_key_parser import code_key_parser


class CodeKeyParserTest(unittest.TestCase):
    def test_ls(self):
        test_data = {'test/a.py': 'awefawefawefawefwaef',
                     'test1/b.py': 'asdfasd',
                     'c.py': '',
                     'test/d.py': 'asdf'}
        result = code_key_parser._decode(code_key_parser._encode(test_data))
        self.assertEqual(result, test_data)


if __name__ == '__main__':
    unittest.main()

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

from fedlearner_webconsole.rpc.auth import SSL_CLIENT_SUBJECT_DN_HEADER
from fedlearner_webconsole.rpc.v2.utils import decode_project_name, encode_project_name, get_pure_domain_from_context


class UtilsTest(unittest.TestCase):

    def test_get_pure_domain_from_context(self):
        mock_context = MagicMock(invocation_metadata=MagicMock(
            return_value={
                SSL_CLIENT_SUBJECT_DN_HEADER: 'CN=*.fl-xxx.com,OU=security,O=security,L=beijing,ST=beijing,C=CN'
            }))
        self.assertEqual(get_pure_domain_from_context(mock_context), 'xxx')

    def test_encode_project_name_anscii(self):
        self.assertEqual(encode_project_name('hello world'), 'hello world')
        self.assertEqual(encode_project_name('-h%20w'), '-h%20w')

    def test_encode_project_name_unicode(self):
        self.assertEqual(encode_project_name('这是一个测试的名字'), '6L+Z5piv5LiA5Liq5rWL6K+V55qE5ZCN5a2X')
        self.assertEqual(encode_project_name('中文 & en'), '5Lit5paHICYgZW4=')

    def test_decode_project_name_anscii(self):
        self.assertEqual(decode_project_name('hello world'), 'hello world')
        self.assertEqual(decode_project_name('-h%20w'), '-h%20w')

    def test_decode_project_name_unicode(self):
        self.assertEqual(decode_project_name('6L+Z5piv5LiA5Liq5rWL6K+V55qE5ZCN5a2X'), '这是一个测试的名字')
        self.assertEqual(decode_project_name('5Lit5paHICYgZW4='), '中文 & en')


if __name__ == '__main__':
    unittest.main()

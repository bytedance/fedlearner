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

from fedlearner_webconsole.rpc.auth import get_common_name


class AuthTest(unittest.TestCase):

    def test_get_common_name(self):
        self.assertIsNone(get_common_name('invalid'))
        self.assertIsNone(get_common_name('CN*.fl-xxx.com,C=CN'))
        self.assertEqual(get_common_name('CN=*.fl-xxx.com,OU=security,O=security,L=beijing,ST=beijing,C=CN'),
                         '*.fl-xxx.com')
        self.assertEqual(get_common_name('CN=aaa.fedlearner.net,OU=security,O=security,L=beijing,ST=beijing,C=CN'),
                         'aaa.fedlearner.net')
        self.assertEqual(get_common_name('CN==*.fl-xxx.com,C=CN'), '=*.fl-xxx.com')


if __name__ == '__main__':
    unittest.main()

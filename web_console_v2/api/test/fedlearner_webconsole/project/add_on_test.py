# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

import os
import unittest
from base64 import b64decode, b64encode
from fedlearner_webconsole.project.add_on import _parse_certificates


class ProjectApisTest(unittest.TestCase):

    def test_parse_certificates(self):
        file_names = [
            'client/client.pem', 'client/client.key', 'client/intermediate.pem', 'client/root.pem',
            'server/server.pem', 'server/server.key', 'server/intermediate.pem', 'server/root.pem'
        ]
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               'test.tar.gz'), 'rb') as file:
            certificates = _parse_certificates(b64encode(file.read()))
        for file_name in file_names:
            self.assertEqual(str(b64decode(certificates.get(file_name)), encoding='utf-8'),
                             'test {}'.format(file_name))


if __name__ == '__main__':
    unittest.main()

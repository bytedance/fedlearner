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

import unittest
from base64 import b64decode
from fedlearner_webconsole.project.apis import _convert_certificates, _CERTIFICATE_FILE_NAMES


class ProjectApisTest(unittest.TestCase):

    def test_convert_certificates(self):
        TEST_ENCODED_CERTIFICATES = ('H4sIAHfi0V8AA+3Z0W6CMBiGYS6FK3Btacv1mFkTsqELdkt2'
                                     '92thBz1gOhNam/g+J9VAAsnnB/Lj3cW/NHmJoDdmWe2yCqWX'
                                     'ddHIrre6s0LYvhFSxs2tyXxes8+L309t2+wP43C6sl/Y7Xgs'
                                     'cUJl+Zj/xU1fbsr2M/h3/qIX0qiQv+pUR/4lpPkPJ++m0R2G'
                                     'vXe7DzdudYwYsNX67/w7/dt/o6wRIX9jRMhfbHUC15C/bzPn'
                                     'j3ql/V+W3Zv73vYYN/uvbNJ/G/ofPhn6X0La/1z5o14r/d/8'
                                     'yn9X/62c+68V/S9hpf/c+Z9I2v/pfPY50r/d//T/fxf7L6Sl'
                                     '/yWk/c+VP+o19//1fXCnfGPAu+Y/Usf5j+ol858S0vyrmP/o'
                                     'OP8z2miu/yXM1//M+aNeaf+X5cHPfzrOf7UyPf0vIe1/rvxR'
                                     'r7T/VTz/6bA9fqH/RaT95/nv+azc/x/7/qcz8/2/Z/5bxMr9'
                                     'n/c/AAAAAAAAAAAAAAAAAAAAQKV+AO42se8AUAAA')
        certificates = _convert_certificates(TEST_ENCODED_CERTIFICATES)
        for file_name in _CERTIFICATE_FILE_NAMES:
            self.assertEqual(str(b64decode(certificates.get(file_name)), encoding='utf-8'),
                             'test {}'.format(file_name))

if __name__ == '__main__':
    unittest.main()

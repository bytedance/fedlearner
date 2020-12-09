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
        TEST_ENCODED_CERTIFICATES = ('H4sIAMBIz18AA+2Z326DIBSHvd5T8AQd/w48j2lpYjbt'
                                     'gmzJ3n4IrmULszFRzOr5bs5FTaD99TsgONO752pdKKUa'
                                     'gISqYqVcxjpCmNBKKCkZU4QyLqioCKw8r8B772rrp1Kf'
                                     '2qabeM4/dj5PfD5+j2v9J7gh/97YD2NX+xvMyZ9z5vMX'
                                     'iirMvwQh/+NrY7r12sCc/KkWQ/6g0P8ipPnHcjhat+wY'
                                     '/vfwyU7kz6/5Cw1D/wcAXhG67DTyYP6O3IJ/2no+SFky'
                                     '/tvLxR3eTLvYGPf9h1v/l9r7r4BL9L8Eqf/fwWMT2A8Z'
                                     '/5vOGduaU1M7s0gfuOu/gJ/7P045E+h/CVL/fwePfeDx'
                                     'yfj/Yj6XHWPW/l/ruP8H9L8Eqf8+eFR+Z6Tnf7Fsu/6z'
                                     'cf3XuP8vQvD/j+CxGTw+Gf83ff+P5/8KtEL/S5D6j+//'
                                     '+yPj/5b7f8lguP8BxfH8vwip/7j/3x8Z/7e8/5NM0uA/'
                                     'w/W/CKn/eP+HIAiyH74AX0xcwQAqAAA=')
        certificates = _convert_certificates(TEST_ENCODED_CERTIFICATES)
        for file_name in _CERTIFICATE_FILE_NAMES:
            self.assertEqual(str(b64decode(certificates.get(file_name)), encoding='utf-8'),
                             'test {}\n'.format(file_name))


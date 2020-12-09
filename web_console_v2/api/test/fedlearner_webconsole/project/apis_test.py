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
        TEST_ENCODED_CERTIFICATES = ('H4sIAKNx0F8AA+2aPW/TQBjHDRIgGGBjvoXVvdfH7VAJti4IBB3Y'
                                     'kOVcJYs4iRyDyqfogsR34EMwsPAFmBCfAql773ylPiI3SUXuUurn'
                                     'J1mXFyd3zl+/e86npG8bPW+SoFBKM6VI24JrKZeutQghCRMZCJCS'
                                     'MSCUcSkhITTssBzv501em6Hko6qcLDnPnHZ0tOR9dynkov1fuPP4'
                                     'XnI7SZ7nBXnxmrwh59jXkvvm4Ob4Yg77/Nd6X/ns8PDV+UP7iU/m'
                                     'OFg45Vb3+qNiWqX5bDbWaZUX47arH98f3v26//Tnyefi9NuTk9//'
                                     'fplIPy/z4wOdj3S9E24eWOU/FbDgv+SUJeQ4zHD+ZuD+C0qqpqz0'
                                     'PgOaSba3t8tTIdWuZFzwB9seHRIaa/1O4D5W+m98Waj/goqEqMDj'
                                     'ahm4/23+c11/MBUgVB/r5i9pRpniJn8BmH8c2vyLcakn4aaBK+XP'
                                     'pM1fKYb5x8DPv5w0uq70qMwbnc50tak+zO9hZvZl6z91kb8CavKH'
                                     'TDC8/4uBzZ9ckj8u/24+vv+u2aT5jpX+86zzP7P1XymJ/kfB97/L'
                                     'H80fCr7/9XQawP51/O/qP1Bb/xUXEv2Pge//n/zR/uHQU//f6Y+b'
                                     '7eNK9V/Jtv4riv7HoKf+m/xxBhgK/v7fdbj/h3b/BzLA9X8UWv8v'
                                     'yR9ngZuP779rtlv/wdwLmPoPPEP/Y+D73+WP5g+FHv+3uv8HQjr/'
                                     'cf0fhR7/sfIPCN//a7H/x93+H+D/P6Pg+4/7fwiCIMPhDMXODNgAMgAA')
        certificates = _convert_certificates(TEST_ENCODED_CERTIFICATES)
        for file_name in _CERTIFICATE_FILE_NAMES:
            self.assertEqual(str(b64decode(certificates.get(file_name)), encoding='utf-8'),
                             'test {}\n'.format(file_name))


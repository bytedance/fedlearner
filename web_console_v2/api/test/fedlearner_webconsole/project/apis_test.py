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
            self.assertEqual(certificates.get(file_name), 'test {}'.format(file_name))

    def test_convert_unicode_certificates(self):
        TEST_UNICODE_ENCODED_CERTIFICATES = ('H4sIANHg0V8AA+2bz2vTYBjHM0FFhz8O4sGDBMRr9v5+m8NA8bKL'
                                             'bLgdBgojtJmUNdtoM5kXxZvgYRfBs0f9G8TDLl68CO6gDAT/AA+C'
                                             'oDffJNWmWbamM+/b2D4fCGnTt3nTPv2+z/d589ZZCf1OaGkFISQ5'
                                             't+O9SPaIsGQfQSmzMZWCUYGQkDbChDFp2UjvZSVsdUKvrS7FawTN'
                                             '9SPaqWarq0e8nnwU++/+f+Hk5dPWCcu67dXt+UV72e4SHbPOqI2o'
                                             '7bXaouf7xU55c2npTvdh9I7napvLNJnqHb9Q3wgcb3Oz5TuBV2/F'
                                             'XX18d/7U29kbn3de1H/sXt/5/u8fE8hnwdue872G357RNw4M0j+i'
                                             'IqN/RhCx7G09l9PPhOufIjsIm4E/i4UKUs11GXUkcRFDxGVnR311'
                                             'gG4i1c9o7mOg/pVeMvmfImbZXPN1xUy4/uP4d/z2A5UBdPVROP5I'
                                             'IsyJir/6IVCIvwni+NdbTX9d3zAwVPwxi+LPOYb4myAdf2eluR76'
                                             '7cBvNL3Qdzb9oJw+1PchGDs8/oz8qf84ESzSv8ScQf1nhCL131cr'
                                             'rv+mLhU7Za/+i9/xRm3LmSYnuscvWtaVXv3X8jrhVsdvNNTP79rC'
                                             'Yrfte+uQOlHufViJGjybdlBy0ulz+/MvP9168mrvfnB17fGX438t'
                                             'k0Ja/71asNxxYJD+EeX9+icqEQio/0xA3L76TxLKnBqnAmMo/yaB'
                                             'tP71ZP8i+s/mfyEp5H8jRPG3NccfqC79/j95UHbsh/P/SOmfSy5A'
                                             '/0YYA///bffnTHJS8P/Dku//yx0HBud/kdG/5BiD/zdB5v6P8v/E'
                                             'oTUpEJeIQgEw9qT1ryf7F9A/yeqfcwrrP4yQ9v+64g9Ul37/397Y'
                                             'GIH++/0/j/TPJAL9G2EM/P+jX3dh/v+Y5Pv/cseB4fx/pH9JCAX/'
                                             'b4KD/l86NcIkqyHkgv8fe9L615P9i/j/A/mfwPpvM6T9v674A9Ul'
                                             'd/5/zX9YZh9D+X8a619KDPo3whj4/3uzT8H/H5Mj5/9LGgeG8v+x'
                                             '/qUyAOD/TXDA/xPXYQS7AteoBP8/9uTM/5ec/Yec/0/yP+cE8r8J'
                                             'cub/S48/UF3S//+pxPo/juL1f4KC/k0Q619z/IHqktZ/shtx/uci'
                                             'yv/KBoD+TZDWv674A9UlR/+jXf8jcKx/Av7fCDn6h8w/QaT1X4n7'
                                             'f5zG9/8krP83Qlr/cP8PAABgcvgNN1wqPwBSAAA=')
        certificates = _convert_certificates(TEST_UNICODE_ENCODED_CERTIFICATES)
        for file_name in _CERTIFICATE_FILE_NAMES:
            self.assertEqual(certificates.get(file_name), 'test {}'.format(file_name))


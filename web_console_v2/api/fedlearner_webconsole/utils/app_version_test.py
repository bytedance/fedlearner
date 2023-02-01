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

from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.utils.app_version import Version, ApplicationVersion


class VersionTest(unittest.TestCase):

    def test_version_number(self):
        v = Version()
        self.assertIsNone(v.version)
        v = Version('non')
        self.assertEqual(v.version, 'non')
        self.assertIsNone(v.major)
        self.assertIsNone(v.minor)
        self.assertIsNone(v.patch)
        v = Version('2.1.33.3')
        self.assertEqual(v.version, '2.1.33.3')
        self.assertEqual(v.major, 2)
        self.assertEqual(v.minor, 1)
        self.assertEqual(v.patch, 33)

    def test_is_standard(self):
        self.assertTrue(Version('2.1.33').is_standard())
        self.assertTrue(Version('2.1.33.1').is_standard())
        self.assertFalse(Version('non').is_standard())

    # Tests == and !=
    def test_eq_and_ne(self):
        v1 = Version('non')
        v2 = Version('non')
        v3 = Version('2.1.33.1')
        v4 = Version('2.1.33')
        v5 = Version('2.1.34')
        self.assertTrue(v1 == v2)
        self.assertFalse(v1 != v2)
        self.assertTrue(v3 == v4)
        self.assertFalse(v3 != v4)
        self.assertFalse(v1 == v3)
        self.assertTrue(v1 != v3)
        self.assertFalse(v4 == v5)
        self.assertTrue(v4 != v5)

    # Tests >
    def test_gt(self):
        v1 = Version('nffff')
        v2 = Version('2.1.33')
        v3 = Version('2.1.34')
        v4 = Version('2.2.33')
        self.assertFalse(v2 > v1)
        self.assertTrue(v3 > v2)
        self.assertFalse(v2 > v3)
        self.assertTrue(v4 > v3)
        self.assertFalse(v3 > v4)
        self.assertTrue(v4 > v2)
        self.assertFalse(v2 > v4)

    # Tests <
    def test_lt(self):
        v1 = Version()
        v2 = Version('1.1.33')
        v3 = Version('2.1.34')
        v4 = Version('2.2.34')
        self.assertFalse(v1 < v2)
        self.assertTrue(v2 < v3)
        self.assertFalse(v3 < v2)
        self.assertTrue(v3 < v4)
        self.assertFalse(v4 < v3)
        self.assertTrue(v2 < v4)
        self.assertFalse(v4 < v2)

    # Tests >=
    def test_ge(self):
        v1 = Version('nffff')
        v2 = Version('2.1.33')
        v3 = Version('2.1.34')
        self.assertFalse(v1 >= v2)
        self.assertFalse(v2 >= v1)
        self.assertTrue(v3 >= v2)
        self.assertFalse(v2 >= v3)

    # Tests <=
    def test_le(self):
        v1 = Version()
        v2 = Version('2.1.33')
        v3 = Version('2.1.34')
        self.assertFalse(v1 <= v2)
        self.assertFalse(v2 <= v1)
        self.assertTrue(v2 <= v3)
        self.assertFalse(v3 <= v2)


class ApplicationVersionTest(unittest.TestCase):

    def test_to_proto(self):
        v = ApplicationVersion(revision='1234234234',
                               branch_name='dev',
                               version='non-standard',
                               pub_date='Fri Jul 16 12:23:19 CST 2021')
        self.assertEqual(
            v.to_proto(),
            common_pb2.ApplicationVersion(revision='1234234234',
                                          branch_name='dev',
                                          version='non-standard',
                                          pub_date='Fri Jul 16 12:23:19 CST 2021'))


if __name__ == '__main__':
    unittest.main()

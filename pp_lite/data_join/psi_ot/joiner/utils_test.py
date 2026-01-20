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

from pp_lite.data_join.psi_ot.joiner.utils import HashValueSet


class HashValueSetTest(unittest.TestCase):

    def setUp(self) -> None:
        self._hash_value_set = HashValueSet()
        self._hash_value_set.add_raw_values(['1', '2'])

    def test_add(self):
        self.assertDictEqual(
            self._hash_value_set._hash_map,  # pylint: disable=protected-access
            {
                '9304157803607034849': '1',
                '6920640749119438759': '2'
            })

    def test_get(self):
        self.assertEqual(self._hash_value_set.get_raw_value('9304157803607034849'), '1')
        self.assertRaises(Exception, self._hash_value_set.get_raw_value, args=('123'))

    def test_list(self):
        self.assertListEqual(self._hash_value_set.get_hash_value_list(), ['9304157803607034849', '6920640749119438759'])

    def test_exists(self):
        self.assertTrue(self._hash_value_set.exists('9304157803607034849'))
        self.assertFalse(self._hash_value_set.exists('123'))


if __name__ == '__main__':
    unittest.main()

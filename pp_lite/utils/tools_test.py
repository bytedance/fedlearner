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
from pp_lite.utils.tools import get_partition_ids


class ToolsTest(unittest.TestCase):

    def test_get_partition_ids(self):
        self.assertListEqual(get_partition_ids(1, 5, 12), [1, 6, 11])
        self.assertListEqual(get_partition_ids(3, 5, 2), [])
        self.assertListEqual(get_partition_ids(4, 5, 10), [4, 9])
        self.assertListEqual(get_partition_ids(5, 5, 10), [])


if __name__ == '__main__':
    unittest.main()

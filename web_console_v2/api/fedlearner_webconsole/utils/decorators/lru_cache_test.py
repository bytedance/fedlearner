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

import time
import unittest

from fedlearner_webconsole.utils.decorators.lru_cache import lru_cache


class LruCacheTest(unittest.TestCase):

    def test_lru_cache(self):
        count = 0
        count2 = 0

        @lru_cache(timeout=1)
        def test(arg1):
            nonlocal count
            count += 1
            return count

        @lru_cache(timeout=10)
        def test_another(arg2):
            nonlocal count2
            count2 += 1
            return count2

        self.assertEqual(test(1), 1)
        self.assertEqual(test(1), 1)

        self.assertEqual(test(-1), 2)
        self.assertEqual(test(-1), 2)

        self.assertEqual(test_another(1), 1)
        self.assertEqual(test_another(1), 1)

        # test cache expired
        time.sleep(1)
        self.assertEqual(test(1), 3)
        self.assertEqual(test(-1), 4)
        self.assertEqual(test_another(1), 1)


if __name__ == '__main__':
    unittest.main()

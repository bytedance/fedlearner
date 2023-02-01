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
from pp_lite.utils.decorators import retry_fn, timeout_fn


class DecoratorTest(unittest.TestCase):

    def setUp(self) -> None:
        self._res = 0

    def test_timeout_fn(self):

        @timeout_fn(2)
        def func() -> int:
            time.sleep(1)
            return 1

        @timeout_fn(1)
        def some_unstable_func() -> int:
            time.sleep(2)
            return 1

        self.assertEqual(func(), 1)
        with self.assertRaises(TimeoutError):
            some_unstable_func()

    def test_retry_fn(self):

        @retry_fn(4)
        def func():
            self._res = self._res + 2

        @retry_fn(4)
        def some_unstable_func():
            self._res = self._res + 2
            raise TimeoutError

        func()
        self.assertEqual(self._res, 2)
        with self.assertRaises(TimeoutError):
            some_unstable_func()
        self.assertEqual(self._res, 10)


if __name__ == '__main__':
    unittest.main()

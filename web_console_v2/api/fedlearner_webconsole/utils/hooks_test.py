# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

import unittest

from fedlearner_webconsole.utils.hooks import parse_and_get_fn


class HookTest(unittest.TestCase):

    def test_parse_and_get_fn(self):
        # right one
        right_hook = 'testing.test_data.hello:hello'
        self.assertEqual(parse_and_get_fn(right_hook)(), 1)

        # unexisted one
        unexisted_hook = 'hello:hello'
        with self.assertRaises(RuntimeError):
            parse_and_get_fn(unexisted_hook)


if __name__ == '__main__':
    unittest.main()

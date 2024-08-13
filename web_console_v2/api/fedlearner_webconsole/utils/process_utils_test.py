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
from multiprocessing import Queue

from fedlearner_webconsole.utils.process_utils import get_result_by_sub_process


def _fake_sub_process(num: int, q: Queue):
    q.put([num, num + 1])


class SubProcessTestCase(unittest.TestCase):

    def test_sub_process(self):
        result = get_result_by_sub_process(name='fake sub process', target=_fake_sub_process, kwargs={
            'num': 2,
        })
        self.assertEqual(result, [2, 3])


if __name__ == '__main__':
    unittest.main()

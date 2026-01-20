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

import os
import unittest

from envs import Envs
from fedlearner_webconsole.algorithm.transmit.sender import AlgorithmSender
from testing.common import NoWebServerTestCase

_TEST_ALGORITHM_PATH = os.path.join(Envs.BASE_DIR, 'testing/test_data/algorithm/e2e_test')


class AlgorithmSenderTest(NoWebServerTestCase):

    def test_make_algorithm_iterator(self):
        sender = AlgorithmSender(chunk_size=1024)
        data_iterator = sender.make_algorithm_iterator(_TEST_ALGORITHM_PATH)

        hash_resp = next(data_iterator)
        # As tar's hash code is always changing
        self.assertEqual(len(hash_resp.hash), 32)
        # Tar archives have a minimum size of 10240 bytes by default
        chunk_count = 0
        for data in data_iterator:
            chunk_count += 1
            self.assertEqual(len(data.chunk), 1024)
        self.assertEqual(chunk_count, 10)


if __name__ == '__main__':
    unittest.main()

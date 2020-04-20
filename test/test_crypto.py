# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
from fedlearner.model.crypto import paillier


import timeit
import gmpy2

class TestPaillier(unittest.TestCase):
    def test_paillier(self):
        public_key, private_key = paillier.PaillierKeypair.generate_keypair()
        a = 3.14159
        b = 101.0
        cipher_a = public_key.encrypt(a, precision=1e30)
        cipher_b = public_key.encrypt(b, precision=1e30)

        cipher_c = cipher_a + cipher_b
        c = private_key.decrypt(cipher_c)

        self.assertAlmostEqual(c, a + b)


if __name__ == '__main__':
    unittest.main()

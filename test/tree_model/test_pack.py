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

import random
import logging
import unittest
import numpy as np
from fedlearner.model.tree.packing import GradHessPacker
from fedlearner.model.tree.tree import EXPONENT, PRECISION
from fedlearner.model.crypto.paillier import PaillierKeypair


class TestPackGradHess(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestPackGradHess, self).__init__(*args, **kwargs)
        public_key, private_key = PaillierKeypair.generate_keypair()
        self.private_key = private_key
        self.pack = GradHessPacker(public_key, PRECISION, EXPONENT)

    def _test_pack(self, grad, hess):
        """Test GradHessPacker
        compare
        1. the difference between result before and after pack
        2. the difference between sum_grad, sum_hess and the result using pack
        Args:
            grad: the grad for pack
            hess: the hess for pack
        """
        grad_hess_encrypted = self.pack.pack_and_encrypt_grad_hess(grad, hess)
        grad_hess_ciphertext = [i.ciphertext(False) for i in grad_hess_encrypted]
        g, h = self.pack.decrypt_and_unpack_grad_hess(grad_hess_ciphertext, self.private_key)
        np.testing.assert_almost_equal(grad, g, decimal=32)
        np.testing.assert_almost_equal(hess, h, decimal=32)

        sum_g = sum(grad)
        sum_h = sum(hess)

        sgh_encrypt = sum(grad_hess_encrypted)
        sgh_ciphertext = sgh_encrypt.ciphertext(False)
        sg, sh = self.pack.decrypt_and_unpack_grad_hess([sgh_ciphertext], self.private_key)
        np.testing.assert_almost_equal(sum_g, sg)
        np.testing.assert_almost_equal(sum_h, sh)

    def test_pack(self):

        grad = [random.randint(-1e100, 1e100) for i in range(1000)]
        hess = [random.randint(-1e100, 1e100) for i in range(1000)]
        self._test_pack(grad, hess)

        grad = (2 * np.random.random(size=1000) - 1) * 1e6
        hess = (2 * np.random.random(size=1000) - 1) * 1e6
        self._test_pack(grad, hess)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()

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
from fedlearner.model.tree.packing import PackGradHess
from fedlearner.model.tree.tree import EXPONENT, PRECISION
from fedlearner.model.crypto.paillier import PaillierKeypair


class TestPackGradHess(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestPackGradHess, self).__init__(*args, **kwargs)
        public_key, private_key = PaillierKeypair.generate_keypair()
        self.pack = PackGradHess(public_key, private_key, PRECISION, EXPONENT)

    def _test_pack(self, grad, hess):
        """
        compare
        1. the difference between result before and after pack
        2. the difference between sum_grad, sum_hess and the result using pack
        :param grad: the grad for pack
        :param hess: the hess for pack
        :return:
        """
        grad_hess_ciphertext = self.pack.pack_grad_hess(grad, hess)
        g, h = self.pack.unpack_grad_hess(grad_hess_ciphertext)
        np.testing.assert_almost_equal(grad, g, decimal=32)
        np.testing.assert_almost_equal(hess, h, decimal=32)

        sum_g = sum(grad)
        sum_h = sum(hess)

        sgh_ciphertext = self.pack.raw_add(grad_hess_ciphertext)
        sg, sh = self.pack.unpack_grad_hess([sgh_ciphertext])
        np.testing.assert_almost_equal(sum_g, sg)
        np.testing.assert_almost_equal(sum_h, sh)

        grad_hess_encrypt = self.pack.pack_grad_hess(grad,
                                                     hess,
                                                     output='encrypt')
        sgh_encrypt = sum(grad_hess_encrypt)
        sgh_ciphertext = sgh_encrypt.ciphertext(False)
        sg, sh = self.pack.unpack_grad_hess([sgh_ciphertext])
        np.testing.assert_almost_equal(sum_g, sg)
        np.testing.assert_almost_equal(sum_h, sh)

    def test_pack(self):

        grad = [random.randint(-1e50, 1e50) for i in range(1000)]
        hess = [random.randint(-1e50, 1e50) for i in range(1000)]
        self._test_pack(grad, hess)

        grad = (2 * np.random.random(size=1000) - 1) * 1e5
        hess = (2 * np.random.random(size=1000) - 1) * 1e5
        self._test_pack(grad, hess)

        grad = (2 * np.random.random(size=1000) - 1)
        hess = (2 * np.random.random(size=1000) - 1)
        self._test_pack(grad, hess)

        grad = np.random.normal(size=1000) * 1e-6
        hess = np.random.normal(size=1000) * 1e-6
        self._test_pack(grad, hess)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()

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

import math
from fedlearner.model.crypto.fixed_point_number import FixedPointNumber
from fedlearner.model.crypto.paillier import PaillierEncryptedNumber


class PackGradHess:
    def __init__(self, public_key, private_key, precision, exponent):
        """
        Grad Hess Pack
        :param public_key: public_key
        :param private_key: private_key
        :param precision: precision for fixed_point_number
        :param exponent: exponent for fixed_point_number
        """
        self.public_key = public_key
        self.private_key = private_key
        self.precision = precision
        self.exponent = exponent
        n_length = math.frexp(self.public_key.n)[1]
        self.offset = n_length // 2
        bit_length = self.offset - 64
        self._n = 1 << bit_length
        self.max_int = self._n // 2 - 1

    def pack_grad_hess(self, grad, hess, output='ciphertext'):
        """
        Pack Grad and Hess
        :param grad: list of grad value
        :param hess: list of hess value
        :param output: output ciphertext or encrypted number
        :return: ciphertext or encrypted number of packed grad and hess
        """
        grad_plaintext = [
            FixedPointNumber.encode(g, self._n, self.max_int, self.precision)
            for g in grad
        ]
        hess_plaintext = [
            FixedPointNumber.encode(h, self._n, self.max_int, self.precision)
            for h in hess
        ]
        grad_hess_encoding = [
            (g_text.encoding << self.offset) + h_text.encoding
            for g_text, h_text in zip(grad_plaintext, hess_plaintext)
        ]

        grad_hess_ciphertext = [
            self.public_key.raw_encrypt(encoding, random_value=None)
            for encoding in grad_hess_encoding
        ]
        if output == 'ciphertext':
            return grad_hess_ciphertext

        enc_numbers = [
            PaillierEncryptedNumber(self.public_key, i, self.exponent)
            for i in grad_hess_ciphertext
        ]
        return enc_numbers

    def unpack_grad_hess(self, grad_hess_ciphertext):
        """
        Unpack Ciphertext
        :param grad_hess_ciphertext: packed grad and hess ciphertext
        :return: list of grad and hess
        """
        grad_hess_plaintext = [
            self.private_key.raw_decrypt(ciphertext)
            for ciphertext in grad_hess_ciphertext
        ]
        grad_plaintext = [(plaintext >> self.offset) % self._n
                          for plaintext in grad_hess_plaintext]
        hess_plaintext = [
            plaintext % self._n for plaintext in grad_hess_plaintext
        ]
        grad = [
            FixedPointNumber(encoding, self.exponent, self._n,
                             self.max_int).decode()
            for encoding in grad_plaintext
        ]
        hess = [
            FixedPointNumber(encoding, self.exponent, self._n,
                             self.max_int).decode()
            for encoding in hess_plaintext
        ]
        return grad, hess

    def raw_add(self, ciphertexts, nsquare=None):
        """
        raw sum from ciphertexts multiplcation
        :param ciphertexts: list of ciphertexts
        :param nsquare: used in ciphertext multiplication
        :return: ciphertext of the sum
        """
        nsquare = nsquare or self.public_key.nsquare
        cipher_sum = ciphertexts[0] % nsquare
        for i in range(1, len(ciphertexts)):
            cipher_sum *= ciphertexts[i]
            cipher_sum %= nsquare
        return cipher_sum

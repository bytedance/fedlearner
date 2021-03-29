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

# reserve some bits to avoid the result of hess
# addition overflow to the result of grad
RESERVED_BIT = 48


class GradHessPacker:
    """Pack the Plaintext of Grad and Hess
    Attributes:
        public_key: public_key
        private_key: private_key
        precision: precision for fixed_point_number
        exponent: exponent for fixed_point_number
        offset: the offset position to place grad plaintext
        _n: the modulo when scalar is negative
        max_int: the maximum of plaintext absolute value of scalar
    """
    def __init__(self, public_key, precision, exponent):
        """Init GradHessPakcer
        """
        self.public_key = public_key
        self.precision = precision
        self.exponent = exponent
        # the bit length of n in public key
        n_length = math.frexp(self.public_key.n)[1]
        self.offset = n_length // 2
        bit_length = self.offset - RESERVED_BIT
        self._n = 1 << bit_length
        self.max_int = self._n // 2 - 1

    def pack_grad_hess(self, grad, hess):
        """Pack Grad and Hess into Plaintext
        Args:
            grad: list of grad value
            hess: list of hess value
            output: output ciphertext or encrypted number

        Returns:
            Plaintext of packed number
        """
        assert len(grad) == len(
            hess), 'the length of grad and hess list should be equal'
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
        return grad_hess_encoding

    def pack_and_encrypt_grad_hess(self, grad, hess):
        """Pack and Encrypt Grad and Hess
        Args:
            grad: list of grad
            hess: list of hess
        Returns:
            encrypted number of packed grad and hess
        """
        grad_hess_encoding = self.pack_grad_hess(grad, hess)
        grad_hess_ciphertext = [
            self.public_key.raw_encrypt(encoding, random_value=None)
            for encoding in grad_hess_encoding
        ]
        enc_numbers = [
            PaillierEncryptedNumber(self.public_key, i, self.exponent)
            for i in grad_hess_ciphertext
        ]
        return enc_numbers

    def decrypt_and_unpack_grad_hess(self, grad_hess_ciphertext, private_key):
        """Decrypt and Unpack Ciphertext into grad and hess
        Args:
            grad_hess_ciphertext: packed grad and hess ciphertext
            private_key: private_key for decryption
        Returns:
            list of grad and hess
        """
        assert private_key.public_key == self.public_key, \
            'private key is not paired with public key in GradHessPacker'
        grad_hess_plaintext = [
            private_key.raw_decrypt(ciphertext)
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

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
from unittest.mock import MagicMock, patch
from pp_lite.proto import data_join_service_pb2
from pp_lite.rpc.client import DataJoinClient
from pp_lite.data_join.psi_rsa.client.signer import Signer
import rsa
from gmpy2 import powmod  # pylint: disable=no-name-in-module


class SignerTest(unittest.TestCase):

    @patch('pp_lite.rpc.client.DataJoinClient.get_public_key')
    def setUp(self, get_public_key) -> None:
        get_public_key.return_value = data_join_service_pb2.PublicKeyResponse(n=str(9376987687101647609), e=str(65537))
        self.private_key = rsa.PrivateKey(9376987687101647609, 65537, 332945516441048573, 15236990059, 615409451)
        self.client = DataJoinClient()
        self.signer = Signer(client=self.client)

    def test_sign(self):
        self.signer._client.sign = MagicMock(  # pylint: disable=protected-access
            side_effect=lambda x: data_join_service_pb2.SignResponse(
                signed_ids=[str(powmod(int(i), self.private_key.d, self.private_key.n)) for i in x]))

        signed_ids = self.signer.sign_batch(['1', '2', '3'])
        correct_signed_ids = ['288f534080870918', '19ade65d522c7915', 'ab2fa2127da06b98']
        self.assertEqual(signed_ids, correct_signed_ids)


if __name__ == '__main__':
    unittest.main()

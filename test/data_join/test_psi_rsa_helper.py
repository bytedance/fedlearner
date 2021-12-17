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

import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile
from google.protobuf import empty_pb2

from fedlearner.data_join import common
from fedlearner.data_join.rsa_psi import rsa_psi_helper

class TestPSIHelper(unittest.TestCase):
    def setUp(self):
        self._base_dir = "./test_psi_helpler"
        if gfile.Exists(self._base_dir):
            gfile.DeleteRecursively(self._base_dir)
        gfile.MakeDirs(self._base_dir)

    def test_helper(self):
        # leader
        public_key = rsa_psi_helper.make_or_load_rsa_keypair_as_pem(2048, self._base_dir);
        self.assertTrue(rsa_psi_helper.load_rsa_key_from_local(self._base_dir, True));

        gfile.DeleteRecursively(self._base_dir)
        gfile.MakeDirs(self._base_dir)
        # follower
        rsa_psi_helper.dump_rsa_key(self._base_dir, public_key, rsa_psi_helper.RSA_KEY_FILENAME)
        self.assertTrue(rsa_psi_helper.load_rsa_key_from_local(self._base_dir));

    def tearDown(self) -> None:
        if gfile.Exists(self._base_dir):
            gfile.DeleteRecursively(self._base_dir)

if __name__ == '__main__':
    unittest.main()

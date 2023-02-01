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

import rsa
import fsspec


def load_private_rsa_key(private_key_path: str) -> rsa.PrivateKey:
    with fsspec.open(private_key_path, mode='rb') as f:
        private_key = rsa.PrivateKey.load_pkcs1(f.read())
    return private_key

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

import argparse
import os
import rsa

import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile

from fedlearner.common.common import set_logger
from fedlearner.data_join.rsa_psi.rsa_psi_signer import RsaPsiSigner

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='RsaPsiSigner cmd.')
    parser.add_argument('-p', '--listen_port', type=int, default=40980,
                        help='Listen port of RSA PSI signer')
    parser.add_argument('--rsa_private_key_path', type=str,
                        help='the file path to store rsa private key')
    parser.add_argument('--rsa_privet_key_pem', type=str,
                        help='the rsa private key stroe by pem format')
    parser.add_argument('--slow_sign_threshold', type=int, default=1,
                        help='the threshold to record as slow sign')
    parser.add_argument('--worker_num', type=int, default=32,
                        help='max worker number for grpc server')
    parser.add_argument('--signer_offload_processor_number', type=int,
                        default=-1, help='the offload processor for signer')
    args = parser.parse_args()
    set_logger()
    rsa_private_key_pem = args.rsa_privet_key_pem
    if rsa_private_key_pem is None or len(rsa_private_key_pem) == 0:
        assert args.rsa_private_key_path is not None
        with gfile.GFile(args.rsa_private_key_path, 'rb') as f:
            rsa_private_key_pem = f.read()
    rsa_private_key = rsa.PrivateKey.load_pkcs1(rsa_private_key_pem)
    offload_processor_number = args.signer_offload_processor_number
    if offload_processor_number < 0:
        offload_processor_number = max(
            1, int(os.environ.get('CPU_LIMIT', '1')) - 1)
    rsa_psi_signer = RsaPsiSigner(rsa_private_key,
                                  offload_processor_number,
                                  args.slow_sign_threshold)
    rsa_psi_signer.run(args.listen_port, args.worker_num)

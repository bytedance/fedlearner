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
import logging
import uuid
import os
import rsa

from tensorflow.compat.v1 import gfile

def dump_rsa_key_as_pem(output_dir, key, fname):
    tmp_fpath = os.path.join(output_dir, str(uuid.uuid1())+'.tmp')
    with gfile.GFile(tmp_fpath, 'w') as wf:
        wf.write(key.save_pkcs1())
    key_fpath = os.path.join(output_dir, fname)
    gfile.Rename(tmp_fpath, key_fpath)

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    parser = argparse.ArgumentParser(description='Rsa Key Generator')
    parser.add_argument('-l', '--rsa_lenght', type=int, required=True,
                        default=1024, help='the bit length for rsa key')
    parser.add_argument('-o', '--output_directory', type=str,
                        default=os.getcwd(),
                        help='the directory to output rsa public/private '\
                             'key, default is current work directory')
    parser.add_argument('--key_prefix', type=str, default='rsa_psi',
                        help='the file name prefix of the dumped ras key')
    args = parser.parse_args()

    pub_key, prv_key = rsa.newkeys(args.rsa_lenght)
    pub_fname = args.key_prefix + '.pub'
    dump_rsa_key_as_pem(args.output_directory, pub_key, pub_fname)
    prv_fname = args.key_prefix
    dump_rsa_key_as_pem(args.output_directory, prv_key, args.key_prefix)
    logging.info('Success dump rsa psi public key: %s\n privat key: %s',
                 os.path.join(args.output_directory, pub_fname),
                 os.path.join(args.output_directory, prv_fname))

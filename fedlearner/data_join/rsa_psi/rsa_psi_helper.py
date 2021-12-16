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

import os
import traceback
import time
import rsa

import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile
from google.protobuf import empty_pb2

from fedlearner.data_join import common
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType

RSA_KEY_FILENAME = "psi_rsa_key.pem"
def rsa_key_filepath(output_base_dir):
    return os.path.join(output_base_dir, RSA_KEY_FILENAME)

def dump_rsa_key(output_dir, key, fname):
    tmp_fpath = common.gen_tmp_fpath(output_dir)
    with gfile.GFile(tmp_fpath, 'w') as wf:
        wf.write(key)
    key_fpath = os.path.join(output_dir, fname)
    gfile.Rename(tmp_fpath, key_fpath)

def dump_rsa_key_as_pem(output_dir, key, fname):
    dump_rsa_key(output_dir, key.save_pkcs1(), fname)

def make_or_load_rsa_keypair_as_pem(length, output_dir,
                                    fname=RSA_KEY_FILENAME):
    """
    Load the key from given path(output_dir/fname), or create
    key pair and persisit it.
    NOTE: This is not suggested to be used in production, KMS is
    more safer instead.
    """
    tmp_fpath = os.path.join(output_dir, fname)
    if gfile.Exists(tmp_fpath):
        return load_rsa_key_from_local(tmp_fpath, True)
    if not gfile.Exists(output_dir):
        gfile.MkDir(output_dir)
    rsa_public_key, rsa_private_key = rsa.newkeys(length)
    dump_rsa_key_as_pem(output_dir, rsa_private_key, fname)
    return rsa_public_key.save_pkcs1()

def load_rsa_key_from_local(input_file, is_sk=False) -> rsa.PublicKey:
    """
    Load key from given input_file for workers with 3 retries.
    Probablly, worker has to wait for the master sycing public key.
    """
    if gfile.IsDirectory(input_file):
        input_file = os.path.join(input_file, RSA_KEY_FILENAME)
    for i in range(3):
        try:
            with gfile.Open(input_file, mode='rb') as f:
                keydata = f.read()
                if is_sk:
                    return rsa.PrivateKey.load_pkcs1(keydata)
                return rsa.PublicKey.load_pkcs1(keydata)
        except Exception as e: #pylint: disable=broad-except
            traceback.print_exc()
            time.sleep(10)
    return None

def load_rsa_key_from_remote(peer_addr, output_dir):
    """
    Follower master syncs public key from remote peer.
    """
    channel = make_insecure_channel(
            peer_addr, ChannelType.REMOTE)
    peer_client = dj_grpc.DataJoinMasterServiceStub(channel)
    for i in range(3):
        try:
            pkres = peer_client.SyncPSIPublicKey(empty_pb2.Empty())
            dump_rsa_key(output_dir, pkres.public_key_pem, RSA_KEY_FILENAME)
            return True
        except Exception as e: #pylint: disable=broad-except
            traceback.print_exc()
            time.sleep(10)
    return None

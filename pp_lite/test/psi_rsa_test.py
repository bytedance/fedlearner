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

import os
import csv
import unittest
import tempfile
import shutil

import rsa
from gmpy2 import powmod  # pylint: disable=no-name-in-module
from cityhash import CityHash64  # pylint: disable=no-name-in-module
# Use ProcessPool to isolate logging config confliction.
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

from pp_lite.data_join import envs
from pp_lite.data_join.psi_rsa.psi_client import run as client_run
from pp_lite.data_join.psi_rsa.psi_server import run as server_run


def sign(raw_id: str, private_key: rsa.PrivateKey) -> str:

    def _sign(i: int):
        return powmod(i, private_key.d, private_key.n).digits()

    return hex(CityHash64(_sign(CityHash64(raw_id))))[2:]


def _make_data(client_input: str, server_input: str, private_key: rsa.PrivateKey, part_num: int, part_size: int,
               ex_size: int):
    if not os.path.exists(client_input):
        os.makedirs(client_input)
    if not os.path.exists(server_input):
        os.makedirs(server_input)
    for part_id in range(part_num):
        client_filename = os.path.join(client_input, f'part-{part_id}')
        server_filename = os.path.join(server_input, f'part-{part_id}')
        client_ids = range(part_id * (part_size + ex_size), part_id * (part_size + ex_size) + part_size)
        server_ids = range(part_id * (part_size + ex_size) + ex_size, (part_id + 1) * (part_size + ex_size))
        server_signed_ids = [sign(str(i), private_key) for i in server_ids]
        with open(client_filename, 'wt', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['raw_id'])
            writer.writeheader()
            writer.writerows([{'raw_id': str(i)} for i in client_ids])
        with open(server_filename, 'wt', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['signed_id'])
            writer.writeheader()
            writer.writerows([{'signed_id': str(i)} for i in server_signed_ids])


class IntegratedTest(unittest.TestCase):

    def setUp(self):
        self._temp_dir = tempfile.mkdtemp()
        envs.STORAGE_ROOT = self._temp_dir
        envs.CLIENT_CONNECT_RETRY_INTERVAL = 1
        self.client_input = os.path.join(self._temp_dir, 'client_input')
        self.server_input = os.path.join(self._temp_dir, 'server_input')
        self.client_output = os.path.join(self._temp_dir, 'client_output')
        self.server_output = os.path.join(self._temp_dir, 'server_output')
        _, private_key = rsa.newkeys(1024)
        _make_data(self.client_input, self.server_input, private_key, 2, 1000, 200)
        self.private_key_path = os.path.join(self.server_input, 'private.key')
        with open(self.private_key_path, 'wb') as f:
            f.write(private_key.save_pkcs1())

    def tearDown(self) -> None:
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    @staticmethod
    def _run_client(input_path, output_path, storage_root: str):
        envs.STORAGE_ROOT = storage_root
        args = {
            'input_dir': input_path,
            'output_dir': output_path,
            'key_column': 'raw_id',
            'server_port': 50058,
            'batch_size': 4096,
            'num_workers': 5,
            'num_sign_parallel': 2,
            'partitioned': False,
            'partition_list': [],
        }
        client_run(args)

    @staticmethod
    def _run_server(input_path: str, output_path: str, private_key_path: str, storage_root: str):
        envs.STORAGE_ROOT = storage_root
        args = {
            'rsa_private_key_path': private_key_path,
            'input_dir': input_path,
            'output_dir': output_path,
            'signed_column': 'signed_id',
            'key_column': 'raw_id',
            'server_port': 50058,
            'batch_size': 4096,
            'num_sign_parallel': 5
        }
        server_run(args=args)

    def test(self):
        futures = []
        with ProcessPoolExecutor(max_workers=2) as pool:
            futures.append(
                pool.submit(self._run_server, self.server_input, self.server_output, self.private_key_path,
                            envs.STORAGE_ROOT))
            futures.append(pool.submit(self._run_client, self.client_input, self.client_output, envs.STORAGE_ROOT))
        for _ in as_completed(futures):
            pass
        with open(os.path.join(self.client_output, 'joined', 'joined.csv'), 'rt', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.assertEqual(len([line['raw_id'] for line in reader]), 1600)
        with open(os.path.join(self.server_output, 'joined', 'output.csv'), 'rt', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.assertEqual(len([line['raw_id'] for line in reader]), 1600)

    def test_client_input_file(self):
        futures = []
        with ProcessPoolExecutor(max_workers=2) as pool:
            futures.append(
                pool.submit(self._run_server, self.server_input, self.server_output, self.private_key_path,
                            envs.STORAGE_ROOT))
            futures.append(
                pool.submit(self._run_client, os.path.join(self.client_input, 'part-0'), self.client_output,
                            envs.STORAGE_ROOT))
        for _ in as_completed(futures):
            pass
        with open(os.path.join(self.client_output, 'joined', 'joined.csv'), 'rt', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.assertEqual(len([line['raw_id'] for line in reader]), 800)
        with open(os.path.join(self.server_output, 'joined', 'output.csv'), 'rt', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.assertEqual(len([line['raw_id'] for line in reader]), 800)


if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    unittest.main()

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

import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from typing import List

import rsa
from gmpy2 import powmod  # pylint: disable=no-name-in-module


class RsaDataJoinSigner():

    def __init__(self, private_key: rsa.PrivateKey, num_workers: int = 1):
        self._private_key = private_key
        self._public_key = rsa.PublicKey(self._private_key.n, self._private_key.e)
        mp_context = multiprocessing.get_context('spawn')
        self._pool = ProcessPoolExecutor(max_workers=num_workers, mp_context=mp_context)

    @property
    def private_key(self) -> rsa.PrivateKey:
        return self._private_key

    @property
    def public_key(self) -> rsa.PublicKey:
        return self._public_key

    @staticmethod
    def _sign_ids(ids: List[int], private_key: rsa.PrivateKey) -> List[int]:
        return [powmod(i, private_key.d, private_key.n) for i in ids]

    def sign_ids(self, ids: List[int]) -> List[int]:

        future = self._pool.submit(self._sign_ids, ids, self._private_key)
        return future.result()

    def stop(self):
        # Processes in the process pool that have not yet exited will block the server process from exiting,
        # so killing each subprocess is needed.
        for pid, process in self._pool._processes.items():  # pylint:disable=protected-access
            process.terminate()
            logging.info(f'send SIGTERM to process {pid}!')
        self._pool.shutdown(wait=True)
        self._pool = None
        logging.info('data join signer stopped')

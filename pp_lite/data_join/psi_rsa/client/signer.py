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
import random
import logging
from typing import List, Tuple, Iterable, Optional
from concurrent.futures import ThreadPoolExecutor

from cityhash import CityHash64  # pylint: disable=no-name-in-module
from gmpy2 import powmod, divm, mpz  # pylint: disable=no-name-in-module

from pp_lite.rpc.client import DataJoinClient
from pp_lite.utils.decorators import time_log
from pp_lite.data_join.utils.generators import make_ids_iterator_from_list


class Signer:

    def __init__(self, client: DataJoinClient, num_workers: Optional[int] = None):
        self._client = client
        self._public_key = self._get_public_key()
        self._pool = None
        if num_workers is not None:
            self._pool = ThreadPoolExecutor(max_workers=num_workers)

    def _get_public_key(self) -> rsa.PublicKey:
        resp = self._client.get_public_key()
        return rsa.PublicKey(int(resp.n), int(resp.e))

    @staticmethod
    def _blind(ids: List[str], public_key: rsa.PublicKey) -> Tuple[List[int], List[int]]:
        """Blind raw id by random number
        blind id by id * r^e % n, where r is the blind number, randomly sampled from (0, 2^256),
        (e, n) is the rsa public key.
        Args:
            ids: list of raw id
            public_key: rsa public key
        Returns:
            blinded id
        """
        blind_numbers = [random.SystemRandom().getrandbits(256) for i in ids]
        hashed_ids = [CityHash64(i) for i in ids]
        e = public_key.e
        n = public_key.n
        blinded_ids = [(powmod(r, e, n) * x) % n for r, x in zip(blind_numbers, hashed_ids)]
        return blinded_ids, blind_numbers

    @staticmethod
    def _deblind(blind_signed_ids: List[int], blind_numbers: List[int], public_key: rsa.PublicKey) -> List[mpz]:
        n = public_key.n
        signed_ids = [divm(x, r, n) for x, r in zip(blind_signed_ids, blind_numbers)]
        return signed_ids

    @staticmethod
    def _one_way_hash(ids: List[int]):
        hashed_ids = [hex(CityHash64(str(i)))[2:] for i in ids]
        return hashed_ids

    def _remote_sign(self, blinded_ids: List[int]):
        blinded_ids = [str(i) for i in blinded_ids]
        resp = self._client.sign(blinded_ids)
        return [int(i) for i in resp.signed_ids]

    def sign_batch(self, ids: List[str]) -> List[str]:
        """Sign raw id by calling service from remote server
        sign id by
            1. generate blind number r;
            2. blind raw id by r: id * r^e % n;
            3. calling blind sign service: id^d * r^d^e % n = id^d * r % n
            4. deblind blinded signed id by r: id^d % n
            5. hash signed id: hash(id^d%n)
        Args:
            ids: raw id
        Returns:
            signed ids
        """
        blinded_ids, blind_numbers = self._blind(ids, self._public_key)
        blinded_signed_ids = self._remote_sign(blinded_ids)
        signed_ids = self._deblind(blinded_signed_ids, blind_numbers, self._public_key)
        hashed_ids = self._one_way_hash(signed_ids)
        return hashed_ids

    def sign_iterator(self, ids_iterator: Iterable[List[str]]):
        if self._pool:
            yield from self._pool.map(self.sign_batch, ids_iterator)
        else:
            for ids in ids_iterator:
                yield self.sign_batch(ids)

    @time_log('Signer')
    def sign_list(self, ids: List[str], batch_size=4096):
        ids_iterator = make_ids_iterator_from_list(ids, batch_size)
        signed_ids = []
        for sids in self.sign_iterator(ids_iterator=ids_iterator):
            signed_ids.extend(sids)
            logging.info(f'[Signer] {len(signed_ids)} ids signed')
        return signed_ids

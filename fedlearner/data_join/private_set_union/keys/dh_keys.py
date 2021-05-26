import json
import os
from hashlib import sha512

import gmpy2

from fedlearner.common.db_client import DBClient
from fedlearner.data_join.common import convert_to_str
from fedlearner.data_join.private_set_union.keys import BaseKeys

PRIME = 'FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020B' \
        'BEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D' \
        '6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A89' \
        '9FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A' \
        '69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C' \
        '354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2' \
        'EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA' \
        '051015728E5A8AACAA68FFFFFFFFFFFFFFFF'
GENERATOR = 2


class DHKeys(BaseKeys):
    def __init__(self,
                 key_dir: str):
        self._mod = gmpy2.mpz(PRIME, base=16)
        self._key_path = os.path.join(key_dir, 'DH')
        self._db_client = DBClient('dfs')
        self._key1, self._key2 = self._get_keys()

    def _get_keys(self):
        keys = self._db_client.get_data(self._key_path)
        if keys:
            keys = json.loads(keys)
            key1 = gmpy2.mpz(keys['key1'], base=62)
            key2 = gmpy2.mpz(keys['key2'], base=62)
        else:
            state = gmpy2.random_state(ord(os.urandom(1)))
            key1 = gmpy2.mpz_random(state, self._mod)
            key2 = gmpy2.mpz_random(state, self._mod)
            key1 = gmpy2.powmod(GENERATOR, key1, self._mod)
            key2 = gmpy2.powmod(GENERATOR, key2, self._mod)
            # use a base of 62 to shrink down the size
            keys = {'key1': key1.digits(62),
                    'key2': key2.digits(62)}
            self._db_client.set_data(self._key_path, json.dumps(keys))
        return key1, key2

    def hash_func(self, item: [bytes, str, int]) -> bytes:
        item = convert_to_str(item)
        return gmpy2.mpz(
            sha512(item.encode()).hexdigest(), base=16
        ).digits(62).encode()

    def encrypt_func1(self, item: bytes) -> bytes:
        item = gmpy2.mpz(item, base=62)
        encrypted = gmpy2.f_mod(item * self._key1, self._mod)
        return encrypted.digits(62).encode()

    def encrypt_func2(self, item: bytes) -> bytes:
        item = gmpy2.mpz(item, base=62)
        encrypted = gmpy2.f_mod(item * self._key2, self._mod)
        return encrypted.digits(62).encode()

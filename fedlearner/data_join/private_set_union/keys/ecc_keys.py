import base64
import json

import pyrelic as pr

from fedlearner.common.db_client import DBClient
from fedlearner.data_join.common import convert_to_bytes
from fedlearner.data_join.private_set_union.keys import BaseKeys
from fedlearner.data_join.private_set_union.utils import Paths


class ECCKeys(BaseKeys):
    def __init__(self):
        self._key_path = Paths.encode_keys_path('ECC')
        self._db_client = DBClient('dfs')
        self._key1, self._key2 = self._get_keys()

    def encode(self, item: pr.G2) -> bytes:
        item = bytes(item)
        return base64.b64encode(item)

    def decode(self, item: bytes) -> pr.G2:
        item = base64.b64decode(item)
        return pr.G2(item)

    def hash(self, item: [bytes, str, int]) -> pr.G2:
        item = convert_to_bytes(item)
        return pr.hash_to_G2(item)

    def encrypt_1(self, item: pr.G2) -> pr.G2:
        assert isinstance(item, pr.G2)
        return item ** self._key1

    def encrypt_2(self, item: pr.G2) -> pr.G2:
        assert isinstance(item, pr.G2)
        return item ** self._key2

    def _get_keys(self):
        keys = self._db_client.get_data(self._key_path)
        if keys:
            keys = json.loads(keys)
            key1 = pr.BN(base64.b64decode(keys['key1']))
            key2 = pr.BN(base64.b64decode(keys['key2']))
        else:
            key1 = pr.rand_BN_order()
            key2 = pr.rand_BN_order()
            keys = {'key1': base64.b64encode(bytes(key1)).decode(),
                    'key2': base64.b64encode(bytes(key2)).decode()}
            self._db_client.set_data(self._key_path, json.dumps(keys))
        return key1, key2

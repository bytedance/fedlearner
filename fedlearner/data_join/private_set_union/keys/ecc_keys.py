import base64
import json
import os

import pyrelic as pr
from tensorflow import gfile

import fedlearner.common.private_set_union_pb2 as psu_pb
from fedlearner.data_join.common import convert_to_bytes
from fedlearner.data_join.private_set_union.keys import BaseKeys


class ECCKeys(BaseKeys):
    def __init__(self, key_info: psu_pb.KeyInfo):
        super().__init__(key_info)
        self._key1, self._key2 = self._get_keys()

    @classmethod
    def key_type(cls):
        return psu_pb.ECC

    def encode(self, item: pr.G2) -> str:
        item = bytes(item)
        return base64.b64encode(item).decode()

    def decode(self, item: str) -> pr.G2:
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
        if gfile.Exists(self._key_path):
            with gfile.GFile(self._key_path) as f:
                keys = json.load(f)
            keys = json.loads(keys)
            key1 = pr.BN(base64.b64decode(keys['key1']))
            key2 = pr.BN(base64.b64decode(keys['key2']))
        else:
            key1 = pr.rand_BN_order()
            key2 = pr.rand_BN_order()
            keys = {'key1': base64.b64encode(bytes(key1)).decode(),
                    'key2': base64.b64encode(bytes(key2)).decode()}
            gfile.MakeDirs(os.path.dirname(self._key_path))
            with gfile.GFile(self._key_path, 'w') as f:
                json.dump(keys, f)
        return key1, key2

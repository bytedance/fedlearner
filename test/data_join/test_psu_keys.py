import os
import random
import string
import unittest

from tensorflow import gfile

from fedlearner.data_join.private_set_union.keys import KEYS


class PSUKeysTest(unittest.TestCase):
    def setUp(self) -> None:
        self._test_root = './test_keys'
        os.environ['STORAGE_ROOT_PATH'] = self._test_root
        if gfile.Exists(self._test_root):
            gfile.DeleteRecursively(self._test_root)

    def test_keys(self):
        for k in KEYS.keys():
            self._test_keys(k)

    def _test_keys(self, key_type: str):
        keys = KEYS[key_type]()
        rnd = ''.join(random.choices(string.ascii_letters + string.digits,
                                     k=10))
        hashed = keys.hash(rnd)
        e1 = keys.encrypt_1(hashed)
        e1 = keys.encrypt_2(e1)

        e2 = keys.encrypt_2(hashed)
        e2 = keys.encode(e2)
        e2 = keys.decode(e2)
        e2 = keys.encrypt_1(e2)
        self.assertEqual(e1, e2)

        dh_key2 = KEYS[key_type]()
        hashed1 = dh_key2.hash(rnd)
        e3 = dh_key2.encrypt_1(hashed1)
        e3 = dh_key2.encrypt_2(e3)

        e4 = dh_key2.encrypt_2(hashed1)
        e4 = dh_key2.encrypt_1(e4)
        self.assertEqual(e3, e4)
        self.assertEqual(e1, e3)
        self.assertEqual(hashed, hashed1)

    def tearDown(self) -> None:
        if gfile.Exists(self._test_root):
            gfile.DeleteRecursively(self._test_root)


if __name__ == '__main__':
    unittest.main()

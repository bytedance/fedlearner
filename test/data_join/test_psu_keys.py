import os
import random
import string
import unittest

from tensorflow import gfile

from fedlearner.data_join.private_set_union.keys import DHKeys


class PSUKeysTest(unittest.TestCase):
    def setUp(self) -> None:
        self._test_root = './test_keys'
        os.environ['STORAGE_ROOT_PATH'] = self._test_root
        if gfile.Exists(self._test_root):
            gfile.DeleteRecursively(self._test_root)

    def test_dh_keys(self):
        dh_key = DHKeys(self._test_root)
        rnd = ''.join(random.choices(string.ascii_letters + string.digits,
                                     k=10))
        hashed = dh_key.hash_func(rnd)
        e1 = dh_key.encrypt_func1(hashed)
        e1 = dh_key.encrypt_func2(e1)

        e2 = dh_key.encrypt_func2(hashed)
        e2 = dh_key.encrypt_func1(e2)
        self.assertEqual(e1, e2)

        dh_key2 = DHKeys(self._test_root)
        hashed1 = dh_key2.hash_func(rnd)
        e3 = dh_key2.encrypt_func1(hashed1)
        e3 = dh_key2.encrypt_func2(e3)

        e4 = dh_key2.encrypt_func2(hashed1)
        e4 = dh_key2.encrypt_func1(e4)
        self.assertEqual(e3, e4)
        self.assertEqual(e1, e3)
        self.assertEqual(hashed, hashed1)

import os
import tempfile
import unittest
import numpy as np
import pandas as pd
import threading
from fedlearner.trainer.bridge import Bridge
from fedlearner.model.crypto.secret_sharing import SecretSharing, MultiTriplets


def make_data(path: str):
    size = 1000000
    x = np.random.randint(10000, size=size).reshape(-1, 1)
    y = np.random.randint(10000, size=size).reshape(-1, 1)
    z = x * y
    follower_x = np.random.randint(10000, size=size).reshape(-1, 1)
    follower_y = np.random.randint(10000, size=size).reshape(-1, 1)
    follower_z = np.random.randint(10000, size=size).reshape(-1, 1)
    leader_x = x - follower_x
    leader_y = y - follower_y
    leader_z = z - follower_z
    alice_beaver_triplets = np.concatenate([leader_x, leader_y, leader_z], axis=1)
    bob_beaver_triplets = np.concatenate([follower_x, follower_y, follower_z], axis=1)
    pd.DataFrame(alice_beaver_triplets).to_csv(os.path.join(path, 'alice_beaver.csv'), header=None, index=False)
    pd.DataFrame(bob_beaver_triplets).to_csv(os.path.join(path, 'bob_beaver.csv'), header=None, index=False)


class TestSecretSharing(unittest.TestCase):

    def leader_test_reveal(self, data: np.ndarray, expected_data: np.ndarray):
        bridge = Bridge('leader', 50051, 'localhost:50052')
        bridge.connect()
        revealed_data = SecretSharing(data, 'leader', bridge).reveal()
        bridge.terminate()
        np.testing.assert_almost_equal(revealed_data, expected_data)

    def follower_test_reveal(self, data: np.ndarray, expected_data: np.ndarray):
        bridge = Bridge('follower', 50052, 'localhost:50051')
        bridge.connect()
        revealed_data = SecretSharing(data, 'follower', bridge).reveal()
        bridge.terminate()
        np.testing.assert_almost_equal(revealed_data, expected_data)

    def leader_test_mul(self, a: np.ndarray, b: np.ndarray, expected_c: np.ndarray, path: str):
        bridge = Bridge('leader', 50053, 'localhost:50054')
        bridge.connect()
        role = 'leader'
        multi_triplets = MultiTriplets(path)
        ss_a = SecretSharing(a, role, bridge, multi_triplets)
        ss_b = SecretSharing(b, role, bridge, multi_triplets)
        ss_c = ss_a * ss_b
        c = SecretSharing(ss_c, role, bridge).reveal()
        bridge.terminate()
        np.testing.assert_almost_equal(c, expected_c)

    def follower_test_mul(self, a: np.ndarray, b: np.ndarray, expected_c: np.ndarray, path: str):
        bridge = Bridge('leader', 50054, 'localhost:50053')
        bridge.connect()
        role = 'follower'
        multi_triplets = MultiTriplets(path)
        ss_a = SecretSharing(a, role, bridge, multi_triplets)
        ss_b = SecretSharing(b, role, bridge, multi_triplets)
        ss_c = ss_a * ss_b
        c = SecretSharing(ss_c, role, bridge).reveal()
        bridge.terminate()
        np.testing.assert_almost_equal(c, expected_c)

    def test_reveal(self):
        data = np.random.randint(100, size=100)
        follower_data = np.random.randint(100, size=100)
        leader_data = data - follower_data

        thread = threading.Thread(target=self.follower_test_reveal, args=(follower_data, data))
        thread.start()
        self.leader_test_reveal(leader_data, data)
        thread.join()

    def test_ss_mul(self):
        size = 100
        a = np.random.randint(10000, size=size)
        b = np.random.randint(10000, size=size)
        follower_a = np.random.randint(10000, size=size)
        follower_b = np.random.randint(10000, size=size)
        leader_a = a - follower_a
        leader_b = b - follower_b
        expected_c = a * b

        with tempfile.TemporaryDirectory() as temp_dir:
            make_data(temp_dir)
            leader_path = os.path.join(temp_dir, 'alice_beaver.csv')
            follower_path = os.path.join(temp_dir, 'bob_beaver.csv')
            thread = threading.Thread(target=self.follower_test_mul, args=(follower_a, follower_b, expected_c, follower_path))
            thread.start()
            self.leader_test_mul(leader_a, leader_b, expected_c, leader_path)
            thread.join()


if __name__ == '__main__':
    unittest.main()

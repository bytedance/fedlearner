from typing import Tuple
import numpy as np
import pandas as pd
from fedlearner.trainer.bridge import Bridge


def reveal(data: np.ndarray, bridge: Bridge) -> np.ndarray:
    bridge.start()
    bridge.send('reveal_data', data)
    peer_data = bridge.receive('reveal_data')
    bridge.commit()
    return data + peer_data


class MultiTriplets:

    def __init__(self, path: str):
        self._reader = pd.read_csv(path, header=None,
                                   index_col=False, iterator=True)

    def get_multi_triplets(self, num: int) -> Tuple[np.ndarray, np.ndarray,
                                                    np.ndarray]:
        df = self._reader.get_chunk(num)
        x = df[0].to_numpy()
        y = df[1].to_numpy()
        z = df[2].to_numpy()
        return x, y, z


class SecretSharing:

    def __init__(self, role: str, data: np.ndarray,
                 multi_triplets: MultiTriplets, bridge: Bridge):
        self.data = data
        self._num = data.size
        self._multi_triplets = multi_triplets
        self._role = role
        self._bridge = bridge

    def __mul__(self, other):
        x, y, z = self._multi_triplets.get_multi_triplets(self._num)
        a = self.data
        b = other.data
        e = a - x
        f = b - y
        E = reveal(e, self._bridge)
        F = reveal(f, self._bridge)

        if self._role == 'leader':
            c = F * x + E * y + z
        else:
            c = F * x + E * y + z + E * F
        return c

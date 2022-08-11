import os
import tempfile
import unittest
import shutil
from pathlib import Path
from threading import Thread

from fedlearner.trainer.bridge import Bridge
from fedlearner.model.tree.trainer import DataBlockLoader, DataBlockInfo


class DataBlockLoaderTest(unittest.TestCase):

    def _make_data(self, path: str):
        Path(os.path.join(path, '0')).mkdir()
        Path(os.path.join(path, '0', '_SUCCESS')).touch()
        Path(os.path.join(path, '0', 'part-r-00000')).touch()
        Path(os.path.join(path, '0', 'part-r-00001')).touch()

    def setUp(self):
        self._leader_data_path = tempfile.mkdtemp()
        self._follower_data_path = tempfile.mkdtemp()
        self._make_data(path=self._leader_data_path)
        self._make_data(path=self._follower_data_path)

    def tearDown(self):
        shutil.rmtree(self._leader_data_path)
        shutil.rmtree(self._follower_data_path)

    def test_get_next_block(self):
        leader_bridge = Bridge(role='leader', listen_port=50051, remote_address='localhost:50052')
        follower_bridge = Bridge(role='follower', listen_port=50052, remote_address='localhost:50051')
        follower_connect = Thread(target=follower_bridge.connect)
        follower_connect.start()
        leader_bridge.connect()
        leader_loader = DataBlockLoader(role='leader', bridge=leader_bridge, data_path=self._leader_data_path, ext=None,
                                        file_wildcard='**/part*')

        follower_loader = DataBlockLoader(role='follower', bridge=follower_bridge, data_path=self._follower_data_path,
                                          ext=None, file_wildcard='**/part*')
        data_block = follower_loader.get_next_block()
        self.assertEqual(data_block,
                         DataBlockInfo(block_id='0/part-r-00000',
                                       data_path=os.path.join(self._follower_data_path, '0/part-r-00000')))
        data_block = follower_loader.get_next_block()
        self.assertEqual(data_block,
                         DataBlockInfo(block_id='0/part-r-00001',
                                       data_path=os.path.join(self._follower_data_path, '0/part-r-00001')))
        data_block = follower_loader.get_next_block()
        self.assertIsNone(data_block)
        data_block = leader_loader.get_next_block()
        self.assertEqual(data_block,
                         DataBlockInfo(block_id='0/part-r-00000', data_path=os.path.join(self._leader_data_path,
                                                                                         '0/part-r-00000')))
        data_block = leader_loader.get_next_block()
        self.assertEqual(data_block,
                         DataBlockInfo(block_id='0/part-r-00001', data_path=os.path.join(self._leader_data_path,
                                                                                         '0/part-r-00001')))
        data_block = leader_loader.get_next_block()
        self.assertIsNone(data_block)


if __name__ == '__main__':
    unittest.main()

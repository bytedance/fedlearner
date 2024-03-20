import os
import tempfile
import unittest
import shutil
import random
from pathlib import Path
from threading import Thread

from fedlearner.trainer.bridge import Bridge
from tensorflow.train import Feature, FloatList, Features, Example, Int64List
from fedlearner.model.tree.trainer import read_data_dir
from fedlearner.model.tree.trainer import DataBlockLoader, DataBlockInfo
import tensorflow as tf
import numpy as np
import csv

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


class MultiprocessingDataReadTest(unittest.TestCase):

    def _make_data(self):
        root = tempfile.mkdtemp()
        record_root = os.path.join(root, 'tfrecord_test')
        csv_root = os.path.join(root, 'csv_test')
        os.mkdir(record_root)
        os.mkdir(csv_root)

        for i in range(5):
            file_name = 'part-' + str(i).zfill(4) + '.tfrecord'
            file_path = os.path.join(record_root, file_name)
            writer = tf.io.TFRecordWriter(file_path)
            for _ in range(5):
                features = {
                    'f_' + str(j): Feature(
                        float_list=FloatList(value=[random.random()])
                    ) for j in range(3)
                }
                features['i_0'] = Feature(
                    int64_list=Int64List(value=[random.randint(0, 100)])
                )
                features['label'] = Feature(
                    int64_list=Int64List(value=[random.randint(0, 1)])
                )
                writer.write(Example(
                        features=Features(feature=features)
                    ).SerializeToString()
                )
            writer.close()

        for i in range(5):
            file_name = 'part-' + str(i).zfill(4) + '.csv'
            file_path = os.path.join(csv_root, file_name)
            with open(file_path, 'w') as file:
                csv_writer = csv.writer(file)
                csv_writer.writerow(['f_0', 'f_1', 'f_2', 'i_0', 'label'])
                for _ in range(5):
                    csv_writer.writerow([
                        random.random(), random.random(), random.random(),
                        random.randint(0, 100), random.randint(0, 1)
                    ])
        return record_root, csv_root

    def test_multiprocessing_data_read(self):
        record_root, csv_root = self._make_data()

        record_1 = read_data_dir(
            '.tfrecord', '*tfrecord', 'tfrecord',
            record_root, False, True, '', 'i_0', 'label', 1)
        record_4 = read_data_dir(
            '.tfrecord', '*tfrecord', 'tfrecord',
            record_root, False, True, '', 'i_0', 'label', 4)
        # result shape:
        # features, cat_features, cont_columns,
        # cat_columns, labels, example_ids, raw_ids
        np.testing.assert_almost_equal(record_1[0], record_4[0])
        np.testing.assert_almost_equal(record_1[1], record_4[1])
        np.testing.assert_almost_equal(record_1[4], record_4[4])

        test_file = os.path.join(record_root, 'part-0000.tfrecord')
        read_data_dir('.tfrecord', '*tfrecord', 'tfrecord', test_file,
                      False, True, '', 'i_0', 'label', 1)
        read_data_dir('.tfrecord', '*tfrecord', 'tfrecord', test_file,
                      False, True, '', 'i_0', 'label', 4)
        np.testing.assert_almost_equal(record_1[0], record_4[0])
        np.testing.assert_almost_equal(record_1[1], record_4[1])
        np.testing.assert_almost_equal(record_1[4], record_4[4])

        csv_1 = read_data_dir('.csv', '*csv', 'csv', csv_root,
                              False, True, '', 'i_0', 'label', 1)
        csv_4 = read_data_dir('.csv', '*csv', 'csv', csv_root,
                              False, True, '', 'i_0', 'label', 4)
        np.testing.assert_almost_equal(csv_1[0], csv_4[0])
        np.testing.assert_almost_equal(csv_1[1], csv_4[1])
        np.testing.assert_almost_equal(csv_1[4], csv_4[4])

        test_file = os.path.join(csv_root, 'part-0000.csv')
        csv_1 = read_data_dir('.csv', '*csv', 'csv', test_file,
                              False, True, '', 'i_0', 'label', 1)
        csv_4 = read_data_dir('.csv', '*csv', 'csv', test_file,
                              False, True, '', 'i_0', 'label', 4)
        np.testing.assert_almost_equal(csv_1[0], csv_4[0])
        np.testing.assert_almost_equal(csv_1[1], csv_4[1])
        np.testing.assert_almost_equal(csv_1[4], csv_4[4])


if __name__ == '__main__':
    unittest.main()

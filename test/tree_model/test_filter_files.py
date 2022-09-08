import os.path
import tempfile
import logging
import unittest
from pathlib import Path
from fedlearner.model.tree.trainer import filter_files

class TestFilterFiles(unittest.TestCase):
    
    def test_filter_files(self):
        path = tempfile.mkdtemp()
        path = Path(path, 'test').resolve()
        path.mkdir()
        path.joinpath('sub_test').mkdir()
        path.joinpath('1.csv').touch()
        path.joinpath('2.csv').touch()
        path.joinpath('3.csv').touch()
        path.joinpath('1.tfrecord').touch()
        path.joinpath('2.tfrecord').touch()
        path.joinpath('3.tfrecord').touch()
        path.joinpath('sub_test').joinpath('sub_sub_test').mkdir()
        path.joinpath('sub_test').joinpath('4.csv').touch()
        path.joinpath('sub_test').joinpath('4.tfrecord').touch()
        path.joinpath('sub_test').joinpath('sub_sub_test').joinpath('5.csv').touch()
        path.joinpath('sub_test').joinpath('sub_sub_test').joinpath('5.tfrecord').touch()

        files = filter_files(str(path), '.csv', '')
        self.assertEqual(len(files), 4)
        files = filter_files(str(path), '', '*tfr*')
        self.assertEqual(len(files), 4)
        files = filter_files(str(path), '', '')
        self.assertEqual(len(files), 8)
        files = filter_files(str(path), '.csv', '*1.*')
        self.assertEqual(len(files), 1)
        files = filter_files((str(os.path.join(path, 'sub_test'))), '', '*csv')
        self.assertEqual(len(files), 2)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from fedlearner.model.tree.trainer import filter_files

class TestFilterFiles(unittest.TestCase):
    
    def test_filter_files(self):
        path = tempfile.mkdtemp()
        path = Path(path, 'test').resolve()
        path.mkdir()
        path.joinpath('test1').mkdir()
        path.joinpath('1.csv').touch()
        path.joinpath('2.csv').touch()
        path.joinpath('3.csv').touch()
        path.joinpath('1.tfrecord').touch()
        path.joinpath('2.tfrecord').touch()
        path.joinpath('3.tfrecord').touch()
        path.joinpath('test1').joinpath('4.csv').touch()
        path.joinpath('test1').joinpath('4.tfrecord').touch()

        files = filter_files(str(path), '.csv', '')
        self.assertEqual(len(files), 3)
        files = filter_files(str(path), '', '*tfr*')
        self.assertEqual(len(files), 3)
        files = filter_files(str(path), '', '')
        self.assertEqual(len(files), 6)
        files = filter_files(str(path), '.csv', '*1.*')
        self.assertEqual(len(files), 1)


if __name__ == '__main__':
    unittest.main()

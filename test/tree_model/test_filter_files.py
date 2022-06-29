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
        path.joinpath('test2').mkdir()
        path.joinpath('3.csv').touch()
        path.joinpath('3.tfrecord').touch()
        path.joinpath('test1').joinpath('1.csv').touch()
        path.joinpath('test1').joinpath('2.tfrecord').touch()
        path.joinpath('test2').joinpath('2.csv').touch()
        path.joinpath('test2').joinpath('1.tfrecord').touch()
        path.joinpath('test1/test').mkdir()
        path.joinpath('test1/test').joinpath('4.csv').touch()
        path.joinpath('test2/test').mkdir()
        path.joinpath('test2/test').joinpath('4.tfrecord').touch()
        
        files = filter_files(path, '')
        self.assertEqual(len(files), 8)
        files = filter_files(path, '*tfrecord')
        self.assertEqual(len(files), 4)
        files = filter_files(path, '*1.*')
        self.assertEqual(len(files), 2)
        files = filter_files(path, '*data')
        self.assertEqual(len(files), 0)


if __name__ == '__main__':
    unittest.main()

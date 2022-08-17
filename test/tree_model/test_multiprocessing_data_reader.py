import os
import random
import tempfile
import unittest
import numpy as np
import csv
import tensorflow.compat.v1 as tf
from tensorflow.train import Feature, FloatList, Features, Example, Int64List
from fedlearner.model.tree.trainer import read_data_dir


class TestBoostingTree(unittest.TestCase):
    def test_multiprocessing_data_read(self):
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
                # Bytes features are not supported at this level of tree model.
                # features['name'] = Feature(
                #     bytes_list=BytesList(
                #         value=[bytes(f'test_1', encoding='utf-8')])
                # )
                features['label'] = Feature(
                    int64_list=Int64List(value=[random.randint(0, 1)])
                )
                writer.write(Example(
                        features=Features(feature=features)
                    ).SerializeToString()
                )
            writer.close()

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
    import logging
    logging.basicConfig(level=logging.INFO)
    unittest.main()

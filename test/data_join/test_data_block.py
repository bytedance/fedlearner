import inspect
import json
import logging
import os
import unittest

import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile

from fedlearner.common.common import set_logger
from fedlearner.data_join.common import partition_repr, DataBlockSuffix
from fedlearner.data_join.raw_data.raw_data import RawData
from fedlearner.data_join.raw_data.common import DataKeyword, OutputType
from fedlearner.data_join.raw_data.raw_data_job import RawDataJob
from test.data_join.test_raw_data import TestDataGenerator, parse_example,\
    convert_tf_example_to_dict


class RawDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self._job_path = "test_data_block_path"
        self._job_name = "test_data_block"

        self._input_dir = "{}/input_data".format(self._job_path)
        self._num_partition = 4
        self._num_item_per_partition = 5
        # generate test data
        generator = TestDataGenerator()
        self._input_data, self._input_files = \
            generator.generate_input_data(
                self._input_dir, self._num_partition,
                self._num_item_per_partition)
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        jar_path = os.path.join(cur_dir, 'jars')
        self._jars = []
        for filename in gfile.ListDirectory(jar_path):
            self._jars.append(os.path.join(jar_path, filename))
        os.environ['SPARK_JARS'] = ','.join(self._jars)

    def tearDown(self) -> None:
        if gfile.Exists(self._job_path):
            gfile.DeleteRecursively(self._job_path)

    def _check_data_block(self,
                          file_paths,
                          wanted_cnts=None,
                          wanted_total_cnt=0):
        total_cnt = 0
        etime_eid_dict = {}
        for idx, fpath in enumerate(sorted(file_paths)):
            segment_cnt = 0
            options = tf.io.TFRecordOptions(compression_type='GZIP')
            logging.info("check %s", fpath)
            for record in tf.python_io.tf_record_iterator(fpath, options):
                tf_item = convert_tf_example_to_dict(parse_example(record))
                print(tf_item[DataKeyword.example_id],
                      tf_item[DataKeyword.event_time])
                event_time = tf_item[DataKeyword.event_time]
                if event_time not in etime_eid_dict:
                    etime_eid_dict[event_time] = []
                etime_eid_dict[event_time].append(
                    tf_item[DataKeyword.example_id].decode())
                segment_cnt += 1
            if wanted_cnts:
                self.assertEqual(segment_cnt, wanted_cnts[idx])
            total_cnt += segment_cnt
        if wanted_cnts:
            self.assertEqual(total_cnt, sum(wanted_cnts))
        else:
            self.assertEqual(total_cnt, wanted_total_cnt)
        self.assertEqual(sorted(etime_eid_dict.keys()),
                         sorted(self._input_data.keys()))
        for etime, eids in etime_eid_dict.items():
            self.assertEqual(sorted(eids),
                             sorted(self._input_data[etime]))

    def test_generate_data_block(self):
        data_block_threshold = 3
        output_path = os.path.join(self._job_path, "data_block")

        json_str = """{
            "input_files": "%s",
            "compression_type": "GZIP",
            "data_block_threshold": %d,
            "output_type": "data_block",
            "output_path": "%s"
        }""" % (','.join(self._input_files),
                data_block_threshold, output_path)
        config = json.loads(json_str)
        processor = RawData(None, self._jars)
        processor.run(config)
        processor.stop()

        total_num = self._num_partition * self._num_item_per_partition
        seg_cnts = []
        while total_num > 0:
            seg_cnts.append(min(data_block_threshold, total_num))
            total_num -= data_block_threshold

        file_paths = []
        for file in gfile.ListDirectory(output_path):
            if file.endswith("gz"):
                file_paths.append(os.path.join(output_path, file))

        self._check_data_block(file_paths, seg_cnts)

    def test_run_data_block(self):
        data_block_threshold = 2
        data_source_name = "test_data_source"
        os.environ['STORAGE_ROOT_PATH'] = self._job_path
        output_path = os.path.join(self._job_path, "raw_data", self._job_name)
        upload_dir = os.path.join(output_path, "upload")
        if not gfile.Exists(upload_dir):
            gfile.MakeDirs(upload_dir)
        entry_file_path = inspect.getfile(RawData)
        file_name = os.path.basename(entry_file_path)
        target_dir = os.path.join(upload_dir, file_name)
        gfile.Copy(entry_file_path, target_dir)
        job = RawDataJob(self._job_name, output_path,
                         output_type=OutputType.DataBlock,
                         data_source_name=data_source_name,
                         data_block_threshold=data_block_threshold,
                         compression_type="GZIP",
                         check_success_tag=True,
                         upload_dir=upload_dir,
                         use_fake_k8s=True)
        job.run(self._input_dir)

        db_path = os.path.join(output_path, 'data_block')
        total_num = self._num_partition * self._num_item_per_partition
        file_paths = []
        for partition_id in range(self._num_partition):
            output_dir = os.path.join(db_path,
                                      partition_repr(partition_id))
            for file in gfile.ListDirectory(output_dir):
                if file.endswith(DataBlockSuffix):
                    file_paths.append(os.path.join(output_dir, file))
        self._check_data_block(file_paths, wanted_total_cnt=total_num)


if __name__ == '__main__':
    set_logger()
    unittest.main()

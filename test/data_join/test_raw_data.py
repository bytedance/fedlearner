from collections import OrderedDict
from datetime import datetime, timedelta
import inspect
import json
import logging
import os
import random
import unittest

from cityhash import CityHash32
import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile

from fedlearner.common.common import set_logger
from fedlearner.data_join.raw_data.raw_data import RawData
from fedlearner.data_join.raw_data.common import DataKeyword, \
    JobType, OutputType
from fedlearner.data_join.raw_data.raw_data_job import RawDataJob


class TestDataGenerator(object):
    @staticmethod
    def _get_input_fpath(output_dir, date_str, partition_id):
        return "{}/{}/partition_{:04}.{}".format(
            output_dir, date_str, partition_id, "gz")

    @staticmethod
    def _get_data(partition_num, num_item_per_partition):
        start_time = datetime.strptime('2021-1-1', '%Y-%m-%d')
        event_times = [
            int((start_time + timedelta(hours=idx)).strftime("%Y%m%d%H%M%S"))
            for idx in range(num_item_per_partition)]
        eid_etime_dict = OrderedDict()
        etime_eid_dict = OrderedDict()

        example_id = 1000001
        for idx in range(partition_num * num_item_per_partition):
            etime_idx = idx % num_item_per_partition
            eid_etime_dict[example_id] = [
                idx, example_id, event_times[etime_idx]]
            if event_times[etime_idx] not in etime_eid_dict:
                etime_eid_dict[event_times[etime_idx]] = []
            etime_eid_dict[event_times[etime_idx]].append(str(example_id))
            example_id += 1
        return event_times, eid_etime_dict, etime_eid_dict

    def _generate_input_partition(self, output_dir,
                                  partition_id,
                                  example_ids,
                                  event_times,
                                  is_dirty):
        types = ['Chinese', 'English', 'Math', 'Physics']
        date_str = str(event_times[0])[:8]
        fpath = self._get_input_fpath(output_dir, date_str, partition_id)
        dirname = os.path.dirname(fpath)
        if not gfile.Exists(dirname):
            gfile.MakeDirs(dirname)
        options = tf.python_io.TFRecordOptions(
            tf.python_io.TFRecordCompressionType.GZIP)
        with tf.io.TFRecordWriter(fpath, options=options) as writer:
            for example_id, event_time in zip(example_ids, event_times):
                feat = {}
                if not is_dirty:
                    feat['example_id'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[
                            str(example_id).encode(
                                'utf-8')]))
                    feat['raw_id'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[
                            str(example_id).encode(
                                'utf-8')]))
                    feat['event_time'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(
                            value=[event_time]))
                if random.random() < 0.8:
                    feat['label'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(
                            value=[random.randint(0, 1)]))
                if random.random() < 0.8:
                    feat['type'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(
                            value=[types[random.randint(0, 3)].encode('utf-8')])
                    )
                example = tf.train.Example(
                    features=tf.train.Features(feature=feat))
                writer.write(example.SerializeToString())
        success_flag_fpath = "{}/_SUCCESS".format(dirname)
        with gfile.GFile(success_flag_fpath, 'w') as fh:
            fh.write('')
        return fpath

    def generate_input_data(self, output_dir, partition_num,
                            num_item_per_partition,
                            is_dirty=False):
        if not gfile.Exists(output_dir):
            gfile.MakeDirs(output_dir)
        start_time = datetime.strptime('2020-7-1', '%Y-%m-%d')
        example_id = 1000001

        etime_eid_dict = OrderedDict()
        output_files = []
        for partition_id in range(partition_num):
            event_times = []
            eids = []
            for idx in range(num_item_per_partition):
                event_times.append(int((start_time + timedelta(
                    hours=idx)).strftime("%Y%m%d%H%M%S")))
                eids.append(example_id)
                etime_eid_dict[event_times[-1]] = [str(example_id)]
                example_id += 1
            filename = self._generate_input_partition(
                output_dir, partition_id,
                eids, event_times, is_dirty)
            output_files.append(filename)
            print(event_times, eids)
            start_time += timedelta(days=1)
        return etime_eid_dict, output_files


def parse_example(record_str):
    try:
        example = tf.train.Example()
        example.ParseFromString(record_str)
        return example
    except Exception as e: # pylint: disable=broad-except
        logging.error("Failed parse tf.Example from record %s, reason %s",
                      record_str, e)
    return None


def convert_tf_example_to_dict(src_tf_example):
    assert isinstance(src_tf_example, tf.train.Example)
    dst_dict = OrderedDict()
    tf_feature = src_tf_example.features.feature
    for key, feat in tf_feature.items():
        if feat.HasField('int64_list'):
            csv_val = [item for item in
                       feat.int64_list.value]  # pylint: disable=unnecessary-comprehension
        elif feat.HasField('bytes_list'):
            csv_val = [item for item in
                       feat.bytes_list.value]  # pylint: disable=unnecessary-comprehension
        elif feat.HasField('float_list'):
            csv_val = [item for item in
                       feat.float_list.value]  # pylint: disable=unnecessary-comprehension
        else:
            assert False, "feat type must in int64, byte, float"
        assert isinstance(csv_val, list)
        dst_dict[key] = csv_val[0] if len(csv_val) == 1 else csv_val
    return dst_dict


class RawDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self._job_path = "test_raw_data_path"
        self._job_name = "test_raw_data"

        self._input_dir = "{}/input_data".format(self._job_path)
        self._num_partition = 4
        self._num_item_per_partition = 5
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        jar_path = os.path.join(cur_dir, 'jars')
        self._jars = []
        for filename in gfile.ListDirectory(jar_path):
            self._jars.append(os.path.join(jar_path, filename))
        os.environ['SPARK_JARS'] = ','.join(self._jars)

    def tearDown(self) -> None:
        if gfile.Exists(self._job_path):
            gfile.DeleteRecursively(self._job_path)

    def _check_raw_data(self, file_paths, wanted_cnt):
        total_cnt = 0
        for fpath in file_paths:
            partition_id = int(fpath.split('-')[-1][:-3])
            print(fpath, partition_id)
            event_time = 0
            options = tf.io.TFRecordOptions(compression_type='GZIP')
            for record in tf.python_io.tf_record_iterator(fpath, options):
                tf_item = convert_tf_example_to_dict(parse_example(record))
                print(tf_item[DataKeyword.example_id],
                      tf_item[DataKeyword.event_time])
                new_event_time = tf_item[DataKeyword.event_time]
                self.assertTrue(new_event_time >= event_time,
                                "{}, {}".format(new_event_time, event_time))
                event_time = new_event_time
                self.assertEqual(partition_id, CityHash32(
                    tf_item[DataKeyword.example_id]) % self._num_partition)
                total_cnt += 1
        self.assertEqual(total_cnt, wanted_cnt)

    def test_generate_raw_data(self):
        # generate test data
        generator = TestDataGenerator()
        self._input_data, self._input_files = \
            generator.generate_input_data(
                self._input_dir, self._num_partition,
                self._num_item_per_partition)

        schema_file_path = os.path.join(self._job_path, "raw_data",
                                        "data.schema.json")
        output_path = os.path.join(self._job_path, "raw_data", str(0))
        output_partition_num = 4

        json_str = """{
            "job_type": "%s",
            "input_files": "%s",
            "schema_path": "%s",
            "output_type": "raw_data",
            "output_path": "%s",
            "output_partition_num": %d
        }""" % (JobType.Streaming, ','.join(self._input_files),
                schema_file_path, output_path, output_partition_num)
        config = json.loads(json_str)
        processor = RawData(None, self._jars)
        processor.run(config)
        processor.stop()

        total_num = self._num_partition * self._num_item_per_partition

        file_paths = []
        for file in gfile.ListDirectory(output_path):
            if file.endswith("gz"):
                file_paths.append(os.path.join(output_path, file))

        self._check_raw_data(file_paths, total_num)

    def test_dirty_input(self):
        # generate test data
        generator = TestDataGenerator()
        self._input_data, self._input_files = \
            generator.generate_input_data(
                self._input_dir, self._num_partition,
                self._num_item_per_partition, is_dirty=True)

        schema_file_path = os.path.join(self._job_path, "raw_data",
                                        "data.schema.json")
        output_path = os.path.join(self._job_path, "raw_data", str(0))
        output_partition_num = 4

        json_str = """{
            "job_type": "%s",
            "input_files": "%s",
            "schema_path": "%s",
            "output_type": "raw_data",
            "output_path": "%s",
            "output_partition_num": %d
        }""" % (JobType.Streaming, ','.join(self._input_files),
                schema_file_path, output_path, output_partition_num)
        config = json.loads(json_str)
        processor = RawData(None, self._jars)
        processor.run(config)
        processor.stop()

        self.assertFalse(gfile.Exists(output_path))

    def test_run_raw_data_dirty(self):
        # generate test data
        generator = TestDataGenerator()
        self._input_data, self._input_files = \
            generator.generate_input_data(
                self._input_dir, self._num_partition,
                self._num_item_per_partition, is_dirty=True)

        output_partition_num = 4
        os.environ['STORAGE_ROOT_PATH'] = self._job_path
        output_path = os.path.join(self._job_path, "raw_data", self._job_name)
        raw_data_publish_dir = os.path.join("portal_publish_dir",
                                            self._job_name)
        upload_dir = os.path.join(output_path, "upload")
        if not gfile.Exists(upload_dir):
            gfile.MakeDirs(upload_dir)
        entry_file_path = inspect.getfile(RawData)
        file_name = os.path.basename(entry_file_path)
        target_dir = os.path.join(upload_dir, file_name)
        gfile.Copy(entry_file_path, target_dir)
        job = RawDataJob(self._job_name, output_path,
                         job_type=JobType.Streaming,
                         output_partition_num=output_partition_num,
                         raw_data_publish_dir=raw_data_publish_dir,
                         output_type=OutputType.RawData,
                         check_success_tag=True,
                         single_subfolder=True,
                         upload_dir=upload_dir,
                         use_fake_k8s=True)
        job.run(self._input_dir)

        for job_id in range(self._num_partition):
            output_dir = os.path.join(output_path, str(job_id))
            self.assertFalse(gfile.Exists(output_dir))

    def test_run_raw_data(self):
        # generate test data
        generator = TestDataGenerator()
        self._input_data, self._input_files = \
            generator.generate_input_data(
                self._input_dir, self._num_partition,
                self._num_item_per_partition)

        output_partition_num = 4
        os.environ['STORAGE_ROOT_PATH'] = self._job_path
        output_path = os.path.join(self._job_path, "raw_data", self._job_name)
        raw_data_publish_dir = os.path.join("portal_publish_dir",
                                            self._job_name)
        upload_dir = os.path.join(output_path, "upload")
        if not gfile.Exists(upload_dir):
            gfile.MakeDirs(upload_dir)
        entry_file_path = inspect.getfile(RawData)
        file_name = os.path.basename(entry_file_path)
        target_dir = os.path.join(upload_dir, file_name)
        gfile.Copy(entry_file_path, target_dir)
        job = RawDataJob(self._job_name, output_path,
                         job_type=JobType.Streaming,
                         output_partition_num=output_partition_num,
                         raw_data_publish_dir=raw_data_publish_dir,
                         output_type=OutputType.RawData,
                         check_success_tag=True,
                         single_subfolder=True,
                         upload_dir=upload_dir,
                         use_fake_k8s=True)
        job.run(self._input_dir)

        for job_id in range(self._num_partition):
            file_paths = []
            output_dir = os.path.join(output_path, str(job_id))
            self.assertTrue(gfile.IsDirectory(output_dir))
            filenames = [file for file in gfile.ListDirectory(output_dir)
                         if not file.startswith(('_', '.'))]
            self.assertEqual(len(filenames), output_partition_num, filenames)
            file_paths.extend([
                os.path.join(output_dir, fname) for fname in filenames
            ])

            self._check_raw_data(file_paths, self._num_item_per_partition)


if __name__ == '__main__':
    set_logger()
    unittest.main()

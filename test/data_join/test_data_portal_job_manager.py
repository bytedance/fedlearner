# Copyright 2021 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

import os
import time
import unittest
import logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from tensorflow.compat.v1 import gfile
from fnmatch import fnmatch

from google.protobuf import text_format

from fedlearner.data_join import common
from fedlearner.common import data_portal_service_pb2 as dp_pb
from fedlearner.common.db_client import DBClient
from fedlearner.data_join.data_portal_job_manager import DataPortalJobManager


class Timer:
    def __init__(self, content):
        self._content = content
        self._start_time = 0

    def __enter__(self):
        self._start_time = time.time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.info("%s takes %s second", self._content,
                     time.time() - self._start_time)


class TestDataPortalJobManager(unittest.TestCase):
    def setUp(self) -> None:
        logging.getLogger().setLevel(logging.DEBUG)
        self._data_portal_name = 'test_data_portal_job_manager'

        self._kvstore = DBClient('etcd', True)
        self._portal_input_base_dir = './portal_input_dir'
        self._portal_output_base_dir = './portal_output_dir'
        self._raw_data_publish_dir = 'raw_data_publish_dir'
        if gfile.Exists(self._portal_input_base_dir):
            gfile.DeleteRecursively(self._portal_input_base_dir)
        gfile.MakeDirs(self._portal_input_base_dir)

        self._data_fnames = ['c/20210101/{}.data'.format(i) for i in range(100)]
        self._data_fnames_without_success = \
            ['a/20210102/{}.data'.format(i) for i in range(100)]
        self._csv_fnames = ['b/20210103/{}.csv'.format(i) for i in range(100)]
        self._unused_fnames = ['{}.xx'.format(100)]
        self._ignored_fnames = [f'.part-{i}.crc' for i in range(10)]
        self._all_fnames = self._data_fnames + \
                           self._data_fnames_without_success + \
                           self._csv_fnames + self._unused_fnames

        all_fnames_with_success = ['c/20210101/_SUCCESS',
                                   'b/20210103/_SUCCESS'] + \
                                  self._all_fnames + self._ignored_fnames
        for fname in all_fnames_with_success:
            fpath = os.path.join(self._portal_input_base_dir, fname)
            gfile.MakeDirs(os.path.dirname(fpath))
            with gfile.Open(fpath, "w") as f:
                f.write('xxx')

    def tearDown(self) -> None:
        gfile.DeleteRecursively(self._portal_input_base_dir)

    def _list_input_dir(self, portal_options, file_wildcard,
                        target_fnames, max_files_per_job=8000):
        portal_manifest = dp_pb.DataPortalManifest(
            name=self._data_portal_name,
            data_portal_type=dp_pb.DataPortalType.Streaming,
            output_partition_num=4,
            input_file_wildcard=file_wildcard,
            input_base_dir=self._portal_input_base_dir,
            output_base_dir=self._portal_output_base_dir,
            raw_data_publish_dir=self._raw_data_publish_dir,
            processing_job_id=-1,
            next_job_id=0
        )
        self._kvstore.set_data(
            common.portal_kvstore_base_dir(self._data_portal_name),
            text_format.MessageToString(portal_manifest))

        with Timer("DataPortalJobManager initialization"):
            data_portal_job_manager = DataPortalJobManager(
                self._kvstore, self._data_portal_name,
                portal_options.long_running,
                portal_options.check_success_tag,
                portal_options.single_subfolder,
                portal_options.files_per_job_limit,
                max_files_per_job,
                start_date=portal_options.start_date,
                end_date=portal_options.end_date
            )
        portal_job = data_portal_job_manager._sync_processing_job()
        target_fnames.sort()
        fpaths = [os.path.join(self._portal_input_base_dir, f)
                  for f in target_fnames]
        self.assertEqual(len(fpaths), len(portal_job.fpaths))
        for index, fpath in enumerate(fpaths):
            self.assertEqual(fpath, portal_job.fpaths[index])

    def test_list_input_dir(self):
        portal_options = dp_pb.DataPotraMasterlOptions(
            use_mock_etcd=True,
            long_running=False,
            check_success_tag=True,
            single_subfolder=False,
            files_per_job_limit=None
        )
        self._list_input_dir(portal_options, "*.data", self._data_fnames)

    def test_list_input_dir_single_folder(self):
        portal_options = dp_pb.DataPotraMasterlOptions(
            use_mock_etcd=True,
            long_running=False,
            check_success_tag=False,
            single_subfolder=True,
            files_per_job_limit=None,
        )
        self._list_input_dir(
            portal_options, "*.data", self._data_fnames)

    def test_list_input_dir_files_limit(self):
        portal_options = dp_pb.DataPotraMasterlOptions(
            use_mock_etcd=True,
            long_running=False,
            check_success_tag=False,
            single_subfolder=False,
            files_per_job_limit=1,
        )
        self._list_input_dir(
            portal_options, "*.data", self._data_fnames)

        portal_options = dp_pb.DataPotraMasterlOptions(
            use_mock_etcd=True,
            long_running=False,
            check_success_tag=False,
            single_subfolder=False,
            files_per_job_limit=150,
        )
        self._list_input_dir(
            portal_options, "*.data", self._data_fnames)

        portal_options = dp_pb.DataPotraMasterlOptions(
            use_mock_etcd=True,
            long_running=False,
            check_success_tag=False,
            single_subfolder=False,
            files_per_job_limit=200,
        )
        self._list_input_dir(
            portal_options, "*.data",
            self._data_fnames + self._data_fnames_without_success)

    def test_list_input_dir_over_limit(self):
        portal_options = dp_pb.DataPotraMasterlOptions(
            use_mock_etcd=True,
            long_running=False,
            check_success_tag=False,
            single_subfolder=False,
        )
        self._list_input_dir(
            portal_options, "*.data", self._data_fnames, max_files_per_job=100)

        self._list_input_dir(
            portal_options, "*.data",
            self._data_fnames + self._data_fnames_without_success,
            max_files_per_job=200)

    def test_list_input_dir_without_success_check(self):
        portal_options = dp_pb.DataPotraMasterlOptions(
            use_mock_etcd=True,
            long_running=False,
            check_success_tag=False,
            single_subfolder=False,
            files_per_job_limit=None
        )
        self._list_input_dir(
            portal_options, "*.data",
            self._data_fnames + self._data_fnames_without_success)

    def test_list_input_dir_without_wildcard(self):
        portal_options = dp_pb.DataPotraMasterlOptions(
            use_mock_etcd=True,
            long_running=False,
            check_success_tag=True,
            single_subfolder=False,
            files_per_job_limit=None
        )
        self._list_input_dir(
            portal_options, None,
            self._data_fnames + self._csv_fnames)

    def test_list_input_dir_without_wildcard_and_success_check(self):
        portal_options = dp_pb.DataPotraMasterlOptions(
            use_mock_etcd=True,
            long_running=False,
            check_success_tag=False,
            single_subfolder=False,
            files_per_job_limit=None
        )
        self._list_input_dir(portal_options, None, self._all_fnames)

    def test_list_input_dir_with_start_date(self):
        portal_options = dp_pb.DataPotraMasterlOptions(
            use_mock_etcd=True,
            long_running=False,
            check_success_tag=False,
            single_subfolder=False,
            files_per_job_limit=None,
            start_date='20210102'
        )
        self._list_input_dir(
            portal_options, None,
            self._data_fnames_without_success + self._csv_fnames
            + self._unused_fnames)

    def test_list_input_dir_with_start_end_date(self):
        portal_options = dp_pb.DataPotraMasterlOptions(
            use_mock_etcd=True,
            long_running=False,
            check_success_tag=False,
            single_subfolder=False,
            files_per_job_limit=None,
            start_date='20210101',
            end_date='20210103'
        )
        self._list_input_dir(
            portal_options, None,
            self._data_fnames + self._data_fnames_without_success
            + self._unused_fnames)

    def test_list_input_dir_with_invalid_date(self):
        portal_options = dp_pb.DataPotraMasterlOptions(
            use_mock_etcd=True,
            long_running=False,
            check_success_tag=False,
            single_subfolder=False,
            files_per_job_limit=None,
            start_date=None,
            end_date='',
        )
        self._list_input_dir(
            portal_options, None, self._all_fnames)


if __name__ == '__main__':
    unittest.main()

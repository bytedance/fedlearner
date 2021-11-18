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
import unittest
import logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from tensorflow.compat.v1 import gfile

from fedlearner.common.db_client import DBClient
from fedlearner.data_join.raw_data.input_data_manager import InputDataManager


class TestInputDataManager(unittest.TestCase):
    def setUp(self) -> None:
        logging.getLogger().setLevel(logging.DEBUG)
        self._data_name = 'test_data_job_manager'

        self._kvstore = DBClient('etcd', True)
        self._input_base_dir = './input_dir'
        self._output_base_dir = './output_dir'
        self._raw_data_publish_dir = 'raw_data_publish_dir'
        if gfile.Exists(self._input_base_dir):
            gfile.DeleteRecursively(self._input_base_dir)
        gfile.MakeDirs(self._input_base_dir)

        self._data_fnames = ['20210101/{}.data'.format(i) for i in range(100)]
        self._data_fnames_without_success = \
            ['20210102/{}.data'.format(i) for i in range(100)]
        self._csv_fnames = ['20210103/{}.csv'.format(i) for i in range(100)]
        self._unused_fnames = ['{}.xx'.format(100)]
        self._all_fnames = self._data_fnames + \
                           self._data_fnames_without_success + \
                           self._csv_fnames + self._unused_fnames

        all_fnames_with_success = ['20210101/_SUCCESS'] + \
                                  ['20210103/_SUCCESS'] +\
                                  self._all_fnames
        for fname in all_fnames_with_success:
            fpath = os.path.join(self._input_base_dir, fname)
            gfile.MakeDirs(os.path.dirname(fpath))
            with gfile.Open(fpath, "w") as f:
                f.write('xxx')

    def tearDown(self) -> None:
        gfile.DeleteRecursively(self._input_base_dir)

    def _list_input_dir(self, file_wildcard, check_success_tag,
                        single_subfolder,
                        target_fnames,
                        max_files_per_job=8000,
                        start_date='',
                        end_date=''):
        manager = InputDataManager(
            file_wildcard,
            check_success_tag,
            single_subfolder,
            max_files_per_job,
            start_date=start_date,
            end_date=end_date)
        fpaths = next(manager.iterator(self._input_base_dir, []))
        fpaths.sort()
        target_fnames.sort()
        target_paths = [os.path.join(self._input_base_dir, f)
                  for f in target_fnames]
        self.assertEqual(len(target_paths), len(fpaths))
        for index, fpath in enumerate(target_paths):
            self.assertEqual(fpath, fpaths[index])

    def test_list_input_dir(self):
        self._list_input_dir(
            file_wildcard="*.data",
            check_success_tag=True,
            single_subfolder=False,
            target_fnames=self._data_fnames)

    def test_list_input_dir_single_folder(self):
        self._list_input_dir(
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=True,
            target_fnames=self._data_fnames)

    def test_list_input_dir_files_limit(self):
        self._list_input_dir(
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames,
            max_files_per_job=1)

        self._list_input_dir(
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames,
            max_files_per_job=150)

        self._list_input_dir(
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames + self._data_fnames_without_success,
            max_files_per_job=200)

    def test_list_input_dir_without_success_check(self):
        self._list_input_dir(
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames + self._data_fnames_without_success)

    def test_list_input_dir_without_wildcard(self):
        self._list_input_dir(
            file_wildcard=None,
            check_success_tag=True,
            single_subfolder=False,
            target_fnames=self._data_fnames + self._csv_fnames)

    def test_list_input_dir_without_wildcard_and_success_check(self):
        self._list_input_dir(
            file_wildcard=None,
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._all_fnames)

    def test_list_input_dir_with_start_date(self):
        self._list_input_dir(
            file_wildcard=None,
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames_without_success +
                          self._csv_fnames + self._unused_fnames,
            start_date="20210102")

    def test_list_input_dir_with_end_date(self):
        self._list_input_dir(
            file_wildcard=None,
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames + self._unused_fnames,
            end_date="20210102")

    def test_list_input_dir_with_start_end_date(self):
        self._list_input_dir(
            file_wildcard=None,
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames +
                          self._data_fnames_without_success +
                          self._unused_fnames,
            start_date="20210101",
            end_date="20210103")

    def test_list_input_dir_invalid_day(self):
        self._list_input_dir(
            file_wildcard=None,
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._all_fnames,
            start_date='dsd',
            end_date='1s')


if __name__ == '__main__':
    unittest.main()

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

from fedlearner.data_join.raw_data.input_data_manager import InputDataManager


class TestInputDataManager(unittest.TestCase):
    def setUp(self) -> None:
        BASIC_FORMAT = "%(asctime)s [%(levelname)s]: %(message)s " \
                       "(%(filename)s:%(lineno)d)"
        logging.basicConfig(format=BASIC_FORMAT)
        logging.getLogger().setLevel(logging.DEBUG)

        self._input_dir = './input_dir'

        self._data_fnames = [
            '{}/20210101/{}.data'.format(self._input_dir, i)
            for i in range(10)]
        self._data_fnames_without_success = \
            ['{}/20210102/{}.data'.format(self._input_dir, i)
            for i in range(10)]
        self._csv_fnames = [
            '{}/20210103/{}.csv'.format(self._input_dir, i) for i in range(10)]
        self._unused_fnames = ['{}/{}.xx'.format(self._input_dir, 10)]
        self._all_fnames = self._data_fnames + \
                           self._data_fnames_without_success + \
                           self._csv_fnames + self._unused_fnames

        self._another_input_dir = './another_input_dir'
        self._another_data_fnames = [
            "{}/20210101/{}.data".format(self._another_input_dir, i)
            for i in range(10)]

        all_fnames_with_success = \
            ['{}/20210101/_SUCCESS'.format(self._input_dir),
             '{}/20210103/_SUCCESS'.format(self._input_dir)] +\
            self._all_fnames + self._another_data_fnames
        for fpath in all_fnames_with_success:
            gfile.MakeDirs(os.path.dirname(fpath))
            with gfile.Open(fpath, "w") as f:
                f.write('xxx')


    def tearDown(self) -> None:
        gfile.DeleteRecursively(self._input_dir)
        gfile.DeleteRecursively(self._another_input_dir)

    def _list_input_dir(self,
                        input_dir,
                        file_wildcard, check_success_tag,
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
        _, fpaths = next(manager.iterator(input_dir, []))
        fpaths.sort()
        target_fnames.sort()
        self.assertEqual(len(target_fnames), len(fpaths))
        for index, fpath in enumerate(target_fnames):
            self.assertEqual(fpath, fpaths[index])

    def test_list_input_dir(self):
        self._list_input_dir(
            self._input_dir,
            file_wildcard="*.data",
            check_success_tag=True,
            single_subfolder=False,
            target_fnames=self._data_fnames)

    def test_list_input_dir_single_folder(self):
        self._list_input_dir(
            self._input_dir,
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=True,
            target_fnames=self._data_fnames)

    def test_list_input_dir_files_limit(self):
        self._list_input_dir(
            self._input_dir,
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames,
            max_files_per_job=1)

        self._list_input_dir(
            self._input_dir,
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames,
            max_files_per_job=15)

        self._list_input_dir(
            self._input_dir,
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames + self._data_fnames_without_success,
            max_files_per_job=20)

    def test_list_input_dir_without_success_check(self):
        self._list_input_dir(
            self._input_dir,
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames + self._data_fnames_without_success)

    def test_list_input_dir_without_wildcard(self):
        self._list_input_dir(
            self._input_dir,
            file_wildcard=None,
            check_success_tag=True,
            single_subfolder=False,
            target_fnames=self._data_fnames + self._csv_fnames)

    def test_list_input_dir_without_wildcard_and_success_check(self):
        self._list_input_dir(
            self._input_dir,
            file_wildcard=None,
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._all_fnames)

    def test_list_input_dir_with_start_date(self):
        self._list_input_dir(
            self._input_dir,
            file_wildcard=None,
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames_without_success +
                          self._csv_fnames + self._unused_fnames,
            start_date="20210102")

    def test_list_input_dir_with_end_date(self):
        self._list_input_dir(
            self._input_dir,
            file_wildcard=None,
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames + self._unused_fnames,
            end_date="20210102")

    def test_list_input_dir_with_start_end_date(self):
        self._list_input_dir(
            self._input_dir,
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
            self._input_dir,
            file_wildcard=None,
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._all_fnames,
            start_date='dsd',
            end_date='1s')

    def test_list_multiple_folders(self):
        input_dirs = ",".join([self._input_dir, self._another_input_dir])
        self._list_input_dir(
            input_dirs,
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames
                          + self._data_fnames_without_success
                          + self._another_data_fnames)

        self._list_input_dir(
            input_dirs,
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=True,
            target_fnames=self._data_fnames
                          + self._another_data_fnames)

    def test_list_multiple_dir_with_limit(self):
        input_dirs = ",".join([self._input_dir, self._another_input_dir])
        self._list_input_dir(
            input_dirs,
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames + self._another_data_fnames,
            max_files_per_job=1)

        self._list_input_dir(
            input_dirs,
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames + self._another_data_fnames,
            max_files_per_job=25)

        self._list_input_dir(
            input_dirs,
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames +
                          self._data_fnames_without_success +
                          self._another_data_fnames,
            max_files_per_job=35)

    def test_list_multiple_dir_with_date(self):
        input_dirs = ",".join([self._input_dir, self._another_input_dir])
        self._list_input_dir(
            input_dirs,
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames +
                          self._another_data_fnames,
            start_date="20210101",
            end_date="20210102")

        self._list_input_dir(
            input_dirs,
            file_wildcard="*.data",
            check_success_tag=False,
            single_subfolder=False,
            target_fnames=self._data_fnames +
                          self._data_fnames_without_success +
                          self._another_data_fnames,
            start_date="20210101")


if __name__ == '__main__':
    unittest.main()

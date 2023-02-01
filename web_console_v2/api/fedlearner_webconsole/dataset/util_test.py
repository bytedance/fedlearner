# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime
import fsspec

from fedlearner_webconsole.dataset.util import get_oldest_daily_folder_time, get_oldest_hourly_folder_time, \
    check_batch_folder_ready, get_dataset_path, add_default_url_scheme, _is_daily, _is_hourly, \
    is_streaming_folder, parse_event_time_to_daily_folder_name, parse_event_time_to_hourly_folder_name, \
    get_export_dataset_name, get_certain_batch_not_ready_err_msg, get_certain_folder_not_ready_err_msg, \
    get_cron_succeeded_msg, get_daily_batch_not_ready_err_msg, get_daily_folder_not_ready_err_msg, \
    get_hourly_batch_not_ready_err_msg, get_hourly_folder_not_ready_err_msg


class UtilsTest(unittest.TestCase):

    @patch('envs.Envs.STORAGE_ROOT', '/test')
    def test_get_dataset_path(self):
        res = get_dataset_path('fake_dataset', 'fake_uuid')
        self.assertEqual(res, 'file:///test/dataset/fake_uuid_fake-dataset')

    def test_get_export_dataset_name(self):
        self.assertEqual(get_export_dataset_name(index=0, input_dataset_name='fake_dataset'), 'export-fake_dataset-0')
        self.assertEqual(
            get_export_dataset_name(index=0, input_dataset_name='fake_dataset', input_data_batch_name='20220101'),
            'export-fake_dataset-20220101-0')

    def test_add_default_url_scheme(self):
        path = add_default_url_scheme('')
        self.assertEqual(path, '')

        path = add_default_url_scheme('/')
        self.assertEqual(path, 'file:///')

        path = add_default_url_scheme('/test/123')
        self.assertEqual(path, 'file:///test/123')

        path = add_default_url_scheme('test/123')
        self.assertEqual(path, 'test/123')

        path = add_default_url_scheme('hdfs:///test/123')
        self.assertEqual(path, 'hdfs:///test/123')

    def test_is_daily(self):
        self.assertTrue(_is_daily('20220701'))
        self.assertFalse(_is_daily('2022711'))
        self.assertFalse(_is_daily('20221711'))
        self.assertFalse(_is_daily('2022x711'))

    def test_is_hourly(self):
        self.assertTrue(_is_hourly('20220701-01'))
        self.assertFalse(_is_hourly('20220711'))
        self.assertFalse(_is_hourly('20220701-1'))
        self.assertFalse(_is_hourly('20220701-25'))

    def test_is_streaming_folder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = os.path.join(tmp_dir, 'test')
            fs, _ = fsspec.core.url_to_fs(test_path)
            fs.mkdirs(os.path.join(test_path, '20220701'))
            fs.mkdirs(os.path.join(test_path, '20220702'))
            fs.mkdirs(os.path.join(test_path, '20220703'))
            res, _ = is_streaming_folder(test_path)
            self.assertTrue(res)

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = os.path.join(tmp_dir, 'test')
            fs, _ = fsspec.core.url_to_fs(test_path)
            fs.mkdirs(os.path.join(test_path, '20220701-01'))
            fs.mkdirs(os.path.join(test_path, '20220701-02'))
            fs.mkdirs(os.path.join(test_path, '20220701-03'))
            res, _ = is_streaming_folder(test_path)
            self.assertTrue(res)

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = os.path.join(tmp_dir, 'test')
            fs, _ = fsspec.core.url_to_fs(test_path)
            fs.mkdirs(test_path)
            res, _ = is_streaming_folder(test_path)
            self.assertFalse(res)

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = os.path.join(tmp_dir, 'test')
            fs, _ = fsspec.core.url_to_fs(test_path)
            fs.mkdirs(os.path.join(test_path, '20221331-25'))
            res, _ = is_streaming_folder(test_path)
            self.assertFalse(res)

    def test_get_oldest_daily_folder_time(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = os.path.join(tmp_dir, 'test')
            fs, _ = fsspec.core.url_to_fs(test_path)
            fs.mkdirs(os.path.join(test_path, '20220701'))
            fs.mkdirs(os.path.join(test_path, '20220702'))
            fs.mkdirs(os.path.join(test_path, '20220703'))
            event_time = get_oldest_daily_folder_time(test_path)
            self.assertEqual(event_time, datetime(2022, 7, 1))
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = os.path.join(tmp_dir, 'test')
            fs, _ = fsspec.core.url_to_fs(test_path)
            fs.mkdirs(os.path.join(test_path, '20220701-01'))
            event_time = get_oldest_daily_folder_time(test_path)
            self.assertIsNone(event_time)

    def test_get_oldest_hourly_folder_time(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = os.path.join(tmp_dir, 'test')
            fs, _ = fsspec.core.url_to_fs(test_path)
            fs.mkdirs(os.path.join(test_path, '20220701-01'))
            fs.mkdirs(os.path.join(test_path, '20220701-02'))
            fs.mkdirs(os.path.join(test_path, '20220701-03'))
            event_time = get_oldest_hourly_folder_time(test_path)
            self.assertEqual(event_time, datetime(2022, 7, 1, 1))
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = os.path.join(tmp_dir, 'test')
            fs, _ = fsspec.core.url_to_fs(test_path)
            fs.mkdirs(os.path.join(test_path, '20220701'))
            event_time = get_oldest_hourly_folder_time(test_path)
            self.assertIsNone(event_time)

    def test_parse_event_time_to_daily_folder_name(self):
        self.assertEqual(parse_event_time_to_daily_folder_name(datetime(2022, 1, 1)), '20220101')

    def test_parse_event_time_to_hourly_folder_name(self):
        self.assertEqual(parse_event_time_to_hourly_folder_name(datetime(2022, 1, 1, 1)), '20220101-01')

    def test_check_batch_folder_ready(self):
        # test no batch_path
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = os.path.join(tmp_dir, 'test')
            fs, _ = fsspec.core.url_to_fs(test_path)
            self.assertFalse(check_batch_folder_ready(folder=test_path, batch_name='20220101'))

        # test no _SUCCESS file
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = os.path.join(tmp_dir, 'test')
            fs, _ = fsspec.core.url_to_fs(test_path)
            fs.mkdirs(os.path.join(test_path, '20220101'))
            self.assertFalse(check_batch_folder_ready(folder=test_path, batch_name='20220101'))

        # test ready
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = os.path.join(tmp_dir, 'test')
            fs, _ = fsspec.core.url_to_fs(test_path)
            fs.mkdirs(os.path.join(test_path, '20220101'))
            fs.touch(os.path.join(test_path, '20220101', '_SUCCESS'))
            self.assertTrue(check_batch_folder_ready(folder=test_path, batch_name='20220101'))

    def test_get_daily_folder_not_ready_err_msg(self):
        self.assertEqual(get_daily_folder_not_ready_err_msg(), '数据源下未找到满足格式要求的文件夹，请确认文件夹以YYYYMMDD格式命名')

    def test_get_hourly_folder_not_ready_err_msg(self):
        self.assertEqual(get_hourly_folder_not_ready_err_msg(), '数据源下未找到满足格式要求的文件夹，请确认文件夹以YYYYMMDD-HH格式命名')

    def test_get_daily_batch_not_ready_err_msg(self):
        self.assertEqual(get_daily_batch_not_ready_err_msg(), '未找到满足格式要求的数据批次，请确保输入数据集有YYYYMMDD格式命名的数据批次')

    def test_get_hourly_batcb_not_ready_err_msg(self):
        self.assertEqual(get_hourly_batch_not_ready_err_msg(), '未找到满足格式要求的数据批次，请确保输入数据集有YYYYMMDD-HH格式命名的数据批次')

    def test_get_certain_folder_not_ready_err_msg(self):
        self.assertEqual(get_certain_folder_not_ready_err_msg(folder_name='20220101-08'),
                         '20220101-08文件夹检查失败，请确认数据源下存在以20220101-08格式命名的文件夹，且文件夹下有_SUCCESS文件')

    def test_get_certain_batch_not_ready_err_msg(self):
        self.assertEqual(get_certain_batch_not_ready_err_msg(batch_name='20220101-08'),
                         '数据批次20220101-08检查失败，请确认该批次命名格式及状态')

    def test_get_cron_succeeded_msg(self):
        self.assertEqual(get_cron_succeeded_msg(batch_name='20220101-08'), '已成功发起20220101-08批次处理任务')


if __name__ == '__main__':
    unittest.main()

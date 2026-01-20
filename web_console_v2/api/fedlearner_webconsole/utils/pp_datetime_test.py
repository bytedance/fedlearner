# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import unittest
from datetime import datetime, timezone, timedelta

from fedlearner_webconsole.utils.pp_datetime import from_timestamp, to_timestamp


class DatetimeTest(unittest.TestCase):

    def test_to_timestamp(self):
        # 2020/12/17 13:58:59 UTC+8
        dt_utc8 = datetime(2020, 12, 17, 13, 58, 59, tzinfo=timezone(timedelta(hours=8)))
        # datetime will be stored without timezone info
        dt_utc8_ts = int(dt_utc8.timestamp()) + 8 * 60 * 60
        self.assertEqual(to_timestamp(dt_utc8.replace(tzinfo=None)), dt_utc8_ts)
        # 2021/04/23 10:42:01 UTC
        dt_utc = datetime(2021, 4, 23, 10, 42, 1, tzinfo=timezone.utc)
        dt_utc_ts = int(dt_utc.timestamp())
        self.assertEqual(to_timestamp(dt_utc), dt_utc_ts)

    def test_from_timestamp(self):
        # 2020/12/17 13:58:59 UTC+8
        dt_utc8 = datetime(2020, 12, 17, 13, 58, 59, tzinfo=timezone(timedelta(hours=8)))
        self.assertEqual(from_timestamp(to_timestamp(dt_utc8)), datetime(2020, 12, 17, 5, 58, 59, tzinfo=timezone.utc))
        dt_utc = datetime(2021, 4, 23, 10, 42, 1, tzinfo=timezone.utc)
        self.assertEqual(from_timestamp(to_timestamp(dt_utc)), datetime(2021, 4, 23, 10, 42, 1, tzinfo=timezone.utc))

    def test_to_timestamp_with_str_input(self):
        dt_str = '2021-04-15T10:43:15Z'
        real_dt = datetime(2021, 4, 15, 10, 43, 15, tzinfo=timezone.utc)
        ts = to_timestamp(dt_str)
        self.assertEqual(real_dt.timestamp(), ts)

        dt_str = '2021-09-24T17:58:27+08:00'
        real_dt = datetime(2021, 9, 24, 17, 58, 27, tzinfo=timezone(timedelta(hours=8)))
        ts = to_timestamp(dt_str)
        self.assertEqual(real_dt.timestamp(), ts)


if __name__ == '__main__':
    unittest.main()

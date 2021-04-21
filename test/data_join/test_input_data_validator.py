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

import unittest

from fedlearner.data_join.raw_data_iter_impl.validator import Validator


class TestInputDataValidator(unittest.TestCase):

    def test_type_checker(self):
        required = {
            "foo": "type(int)",
            "bar": "type(str)datetime(%Y%m%d)"
        }
        optional = {
            "foo1": "type(int)",
            "bar1": "type(float)",
        }
        validator = Validator(required, optional)
        record = {"foo": 123, "bar": "20200102"}
        try:
            validator.check(record)
        except ValueError as e:
            self.fail(e)

        record = {"foo": 123, "bar": "20200102", "bar1": 1}
        try:
            validator.check(record)
        except ValueError as e:
            self.fail(e)

        record = {"foo": "123", "bar": "20200102"}
        try:
            validator.check(record)
        except ValueError as e:
            self.fail(e)

        record = {"foo": "123.", "bar": "20200102"}
        self.assertRaises(ValueError, validator.check, record)

        record = {"foo": 123, "bar": "2020010201"}
        self.assertRaises(ValueError, validator.check, record)

        record = {"foo": 123, "bar": "20200102"}
        with self.assertRaises(ValueError):
            validator.check(record, 3)

        record = {"foo": 123, "foo1": 234, "bar": "20200102"}
        try:
            validator.check(record)
        except ValueError as e:
            self.fail(e)

        record = {"foo1": 123, "bar": "20200102"}
        self.assertRaises(ValueError, validator.check, record)


if __name__ == '__main__':
    unittest.main()

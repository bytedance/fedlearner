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

import unittest
import os
import tempfile
import fsspec

import envs
from error_code import AreaCode, ErrorType, write_termination_message


class ErrorCodeTest(unittest.TestCase):

    def test_write_terminaton_message(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            envs.TERMINATION_LOG_PATH = os.path.join(tmp_dir, 'log_file')
            write_termination_message(AreaCode.FORMAT_CHECKER, ErrorType.DATA_FORMAT_ERROR, 'format check failed')
            expected_errors = '00031001-format check failed'
            with fsspec.open(envs.TERMINATION_LOG_PATH, mode='r') as f:
                errors = f.read()
            self.assertEqual(expected_errors, errors)


if __name__ == '__main__':
    unittest.main()

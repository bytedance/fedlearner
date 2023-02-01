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
import unittest
from unittest.mock import Mock, patch

from click.testing import CliRunner

from pp_lite import cli
from web_console_v2.inspection.error_code import AreaCode, ErrorType


class CliTest(unittest.TestCase):

    # TODO(zhou.yi): create Env class to process environment variables
    @patch('pp_lite.cli.write_termination_message')
    def test_ot_missing_argument(self, mock_write_termination_message: Mock):
        if 'INPUT_PATH' in os.environ:
            del os.environ['INPUT_PATH']

        runner = CliRunner()
        with self.assertLogs(level='ERROR') as cm:
            result = runner.invoke(cli=cli.pp_lite, args='psi-ot client')
        # check logging
        self.assertIn('Environment variable INPUT_PATH is missing.', cm.output[0])

        # check termination log
        mock_write_termination_message.assert_called_once_with(AreaCode.PSI_OT, ErrorType.INPUT_PARAMS_ERROR,
                                                               'Environment variable INPUT_PATH is missing.')

        # check exception that raise again
        self.assertEqual(str(result.exception), '00071005-Environment variable INPUT_PATH is missing.')

    @patch('pp_lite.cli.write_termination_message')
    def test_hash_missing_argument(self, mock_write_termination_message: Mock):
        if 'INPUT_PATH' in os.environ:
            del os.environ['INPUT_PATH']

        runner = CliRunner()
        with self.assertLogs(level='ERROR') as cm:
            result = runner.invoke(cli=cli.pp_lite, args='psi-hash client')

        # check logging
        self.assertIn('Environment variable INPUT_PATH is missing.', cm.output[0])

        # check termination log
        mock_write_termination_message.assert_called_once_with(AreaCode.PSI_HASH, ErrorType.INPUT_PARAMS_ERROR,
                                                               'Environment variable INPUT_PATH is missing.')

        # check exception that raise again
        self.assertEqual(str(result.exception), '00091005-Environment variable INPUT_PATH is missing.')

    @patch('pp_lite.cli.write_termination_message')
    def test_trainer_client_missing_argument(self, mock_write_termination_message: Mock):
        if 'TF_PORT' in os.environ:
            del os.environ['TF_PORT']

        runner = CliRunner()
        with self.assertLogs(level='ERROR') as cm:
            result = runner.invoke(cli=cli.pp_lite, args='trainer client')

        # check logging
        self.assertIn('Environment variable TF_PORT is missing.', cm.output[0])

        # check termination log
        mock_write_termination_message.assert_called_once_with(AreaCode.TRAINER, ErrorType.INPUT_PARAMS_ERROR,
                                                               'Environment variable TF_PORT is missing.')

        # check exception that raise again
        self.assertEqual(str(result.exception), '00101005-Environment variable TF_PORT is missing.')

    @patch('pp_lite.cli.write_termination_message')
    def test_trainer_server_missing_argument(self, mock_write_termination_message: Mock):
        if 'EXPORT_PATH' in os.environ:
            del os.environ['EXPORT_PATH']

        runner = CliRunner()
        with self.assertLogs(level='ERROR') as cm:
            result = runner.invoke(cli=cli.pp_lite, args='trainer server')

        # check logging
        self.assertIn('Environment variable EXPORT_PATH is missing.', cm.output[0])

        # check termination log
        mock_write_termination_message.assert_called_once_with(AreaCode.TRAINER, ErrorType.INPUT_PARAMS_ERROR,
                                                               'Environment variable EXPORT_PATH is missing.')

        # check exception that raise again
        self.assertEqual(str(result.exception), '00101005-Environment variable EXPORT_PATH is missing.')


if __name__ == '__main__':
    unittest.main()

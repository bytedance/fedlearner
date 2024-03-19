# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import unittest
from unittest.mock import MagicMock, patch

from fedlearner_webconsole.middleware.log_filter import RequestIdLogFilter


class RequestIdLogFilterTest(unittest.TestCase):

    @patch('fedlearner_webconsole.middleware.log_filter.get_current_request_id')
    def test_attach_request_id(self, mock_get_current_request_id):
        mock_get_current_request_id.return_value = '123'
        log_record = MagicMock()
        self.assertEqual(RequestIdLogFilter().filter(log_record), True)
        self.assertEqual(log_record.request_id, '123')


if __name__ == '__main__':
    unittest.main()

# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
from http import HTTPStatus

from testing.common import BaseTestCase


class ExceptionHandlersTest(BaseTestCase):
    def test_not_found(self):
        response = self.get_helper('/api/v2/not_found',
                                   use_auth=False)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


if __name__ == '__main__':
    unittest.main()

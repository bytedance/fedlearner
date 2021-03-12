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

import os
import logging
import unittest
from http import HTTPStatus

from testing.common import BaseTestCase

class SettingsApiTest(BaseTestCase):
    def test_update_image(self):
        resp = self.get_helper('/api/v2/settings')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertTrue('webconsole_image' in resp.json['data'])

        resp = self.patch_helper(
            '/api/v2/settings',
            data={
                'webconsole_image': 'test-image'
            })
        self.assertEqual(resp.status_code, HTTPStatus.OK)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()

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

from testing.common import BaseTestCase
from fedlearner_webconsole.auth.models import Role
from fedlearner_webconsole.iam.permission import _DEFAULT_PERMISSIONS


class IamApisTest(BaseTestCase):

    def test_workflow_with_iam(self):
        resp = self.get_helper('/api/v2/iams')
        data = self.get_response_data(resp)
        self.assertEqual(len(data['iams']), len(_DEFAULT_PERMISSIONS[Role.USER]))


if __name__ == '__main__':
    unittest.main()

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
from unittest.mock import MagicMock, patch

from fedlearner_webconsole.utils.images import generate_unified_version_image


class ImageUtilsTest(unittest.TestCase):

    @patch('fedlearner_webconsole.utils.images.SettingService.get_application_version')
    def test_generate_unified_version_image(self, mock_get_application_version: MagicMock):
        mock_version = MagicMock()
        mock_version.version.version = '2.2.2.2'
        mock_get_application_version.return_value = mock_version
        self.assertEqual(generate_unified_version_image('artifact.bytedance.com/fedlearner/pp_data_inspection'),
                         'artifact.bytedance.com/fedlearner/pp_data_inspection:2.2.2.2')
        self.assertEqual(generate_unified_version_image('artifact.bytedance.com/fedlearner/pp_data_inspection:test'),
                         'artifact.bytedance.com/fedlearner/pp_data_inspection:2.2.2.2')


if __name__ == '__main__':
    unittest.main()

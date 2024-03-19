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

from unittest import main, TestCase
from pathlib import Path

from pp_lite.deploy.configs.controllers import get_deploy_config_from_yaml


class ConfigTest(TestCase):

    def test_get_config_from_yaml(self):
        config = get_deploy_config_from_yaml(Path(__file__).parent.parent / 'test_data' / 'deploy_config.yaml')
        self.assertEqual('some_company', config.pure_domain_name)
        self.assertEqual('artifact.bytedance.com/fedlearner/pp_lite:2.3.25.4', config.image_uri)
        self.assertEqual(False, config.include_image)
        self.assertEqual('some_key', config.auto_cert_api_key)


if __name__ == '__main__':
    main()

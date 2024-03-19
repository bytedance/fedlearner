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
import os
import json
import unittest
from unittest.mock import patch

from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow_template.service import dict_to_workflow_definition,\
    dict_to_editor_info, _format_template_with_yaml_editor
from testing.common import BaseTestCase


class MetaYamlTest(BaseTestCase):

    @patch('fedlearner_webconsole.setting.service.SettingService.get_application_version')
    def test_meta_yaml(self, mock_version):
        mock_version.return_value.version.version = '2.2.2.2'
        # test if meta_yaml in frontend is in right form
        editor_info = {'yaml_editor_infos': {}}
        config = {'job_definitions': []}
        meta_yaml_path = 'web_console_v2/client/src/jobMetaDatas'
        for meta_yaml_file in os.listdir(meta_yaml_path):
            job_name = os.path.splitext(meta_yaml_file)[0]
            file_suffix = os.path.splitext(meta_yaml_file)[1]
            if file_suffix == '.metayml':
                with open(f'{meta_yaml_path}/{job_name}.metayml', 'r', encoding='utf-8') as f:
                    metayml = f.read()
                with open(f'{meta_yaml_path}/{job_name}.json', 'r', encoding='utf-8') as f:
                    slots = json.load(f)
            else:
                continue
            editor_info['yaml_editor_infos'][job_name] = {}
            editor_info['yaml_editor_infos'][job_name]['slots'] = slots
            editor_info['yaml_editor_infos'][job_name]['meta_yaml'] = metayml
            config['job_definitions'].append({'name': job_name, 'easy_mode': True})

        editor_info_proto = dict_to_editor_info(editor_info)
        template_proto = dict_to_workflow_definition(config)
        with db.session_scope() as session:
            _format_template_with_yaml_editor(template_proto, editor_info_proto, session)


if __name__ == '__main__':
    unittest.main()

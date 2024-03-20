# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
import tarfile
import base64
from io import BytesIO
from google.protobuf.json_format import ParseDict
from fedlearner_webconsole.job.yaml_formatter import format_yaml, code_dict_encode, generate_self_dict
from fedlearner_webconsole.job.models import Job, JobState
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition
from testing.common import BaseTestCase


class YamlFormatterTest(BaseTestCase):
    def test_format_with_phs(self):
        project = {
            'variables[0]':
                {'storage_root_dir': 'root_dir'}

        }
        workflow = {
            'jobs': {
                'raw_data_job': {'name': 'raw_data123'}
            }
        }
        yaml = format_yaml("""
          {
            "name": "OUTPUT_BASE_DIR",
            "value": "${project.variables[0].storage_root_dir}/raw_data/${workflow.jobs.raw_data_job.name}"
          }
        """, project=project, workflow=workflow)
        self.assertEqual(yaml, """
          {
            "name": "OUTPUT_BASE_DIR",
            "value": "root_dir/raw_data/raw_data123"
          }
        """)

        self.assertEqual(format_yaml('$project.variables[0].storage_root_dir',
                                     project=project),
                         project['variables[0]']['storage_root_dir'])

    def test_format_with_no_ph(self):
        self.assertEqual(format_yaml('{a: 123, b: 234}'),
                         '{a: 123, b: 234}')

    def test_format_yaml_unknown_ph(self):
        x = {
            'y': 123
        }
        with self.assertRaises(RuntimeError) as cm:
            format_yaml('$x.y is $i.j.k', x=x)
        self.assertEqual(str(cm.exception), 'Unknown placeholder: i.j.k')
        with self.assertRaises(RuntimeError) as cm:
            format_yaml('$x.y is ${i.j}', x=x)
        self.assertEqual(str(cm.exception), 'Unknown placeholder: i.j')

    def test_encode_code(self):
        test_data = {'test/a.py': 'awefawefawefawefwaef',
                     'test1/b.py': 'asdfasd',
                     'c.py': '',
                     'test/d.py': 'asdf'}
        code_base64 = code_dict_encode(test_data)
        code_dict = {}
        if code_base64.startswith('base64://'):
            tar_binary = BytesIO(base64.b64decode(code_base64[9:]))
            with tarfile.open(fileobj=tar_binary) as tar:
                for file in tar.getmembers():
                    code_dict[file.name] = str(tar.extractfile(file).read(),
                                               encoding='utf-8')
        self.assertEqual(code_dict, test_data)

    def test_generate_self_dict(self):
        config = {
            'variables': [
                {
                    'name': 'namespace',
                    'value': 'leader'
                },
                {
                    'name': 'basic_envs',
                    'value': '{}'
                },
                {
                    'name': 'storage_root_dir',
                    'value': '/'
                },
                {
                    'name': 'EGRESS_URL',
                    'value': '127.0.0.1:1991'
                }
            ]
        }
        job = Job(name='aa', project_id=1, workflow_id=1, state=JobState.NEW)
        job.set_config(ParseDict(config, JobDefinition()))
        self.assertEqual(generate_self_dict(job),
                         {'id': None, 'name': 'aa',
                          'job_type': None, 'state': 'NEW', 'config':
                              {'expert_mode': False,
                               'variables': [
                                   {
                                       'name': 'namespace',
                                       'value': 'leader',
                                       'access_mode': 'UNSPECIFIED',
                                       'widget_schema': '',
                                       'value_type': 'STRING'},
                                   {
                                       'name': 'basic_envs',
                                       'value': '{}',
                                       'access_mode': 'UNSPECIFIED',
                                       'widget_schema': '',
                                       'value_type': 'STRING'},
                                   {
                                       'name': 'storage_root_dir',
                                       'value': '/',
                                       'access_mode': 'UNSPECIFIED',
                                       'widget_schema': '',
                                       'value_type': 'STRING'},
                                   {
                                       'name': 'EGRESS_URL',
                                       'value': '127.0.0.1:1991',
                                       'access_mode': 'UNSPECIFIED',
                                       'widget_schema': '',
                                       'value_type': 'STRING'}],
                               'name': '',
                               'job_type': 'UNSPECIFIED',
                               'is_federated': False,
                               'dependencies': [],
                               'yaml_template': ''},
                          'is_disabled': None, 'workflow_id': 1, 'project_id': 1, 'flapp_snapshot': None,
                          'pods_snapshot': None, 'error_message': None, 'created_at': None, 'updated_at': None,
                          'deleted_at': None, 'pods': [], 'complete_at': None,
                          'variables': {'namespace': 'leader', 'basic_envs': '{}', 'storage_root_dir': '/',
                                        'EGRESS_URL': '127.0.0.1:1991'}}
                         )


if __name__ == '__main__':
    unittest.main()

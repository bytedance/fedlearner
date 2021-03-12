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

from fedlearner_webconsole.job.yaml_formatter import format_yaml


class YamlFormatterTest(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()

# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import unittest
from fedlearner_webconsole.utils.pp_yaml import compile_yaml_template, extract_flapp_envs, _to_bool, \
    _to_dict, _to_int, \
    _to_float, _to_list


def test_postprocessor(loaded_json: dict):
    loaded_json['test'] = 1
    return loaded_json


class YamlTestCase(unittest.TestCase):

    def test_compile_yaml_template(self):
        result = compile_yaml_template('{"test${a.b}": 1}', [], use_old_formater=True, a={'b': 'placeholder'})
        self.assertEqual(result, {'testplaceholder': 1})

    def test_compile_yaml_template_with_postprocessor(self):
        result = compile_yaml_template('{"test${a.b}": 1}', [test_postprocessor],
                                       use_old_formater=True,
                                       a={'b': 'placeholder'})
        self.assertEqual(result, {'testplaceholder': 1, 'test': 1})

    def test_compile_yaml_template_with_list_merge(self):
        result = compile_yaml_template('[{"test": false}]+${a.b}', [], use_old_formater=True, a={'b': '[{True: true}]'})
        self.assertEqual(result, [{'test': False}, {True: True}])
        result = compile_yaml_template('[{"test": false}]+${a.b}', [],
                                       use_old_formater=True,
                                       a={'b': [{
                                           'test': False
                                       }]})
        self.assertEqual(result, [{'test': False}, {'test': False}])
        result = compile_yaml_template('${a.b}', [], use_old_formater=True, a={'b': {'v': 123}})
        self.assertEqual(result, {'v': 123})

    def test_extract_flapp_evs(self):
        flapp_json = {
            'kind': 'FLApp',
            'spec': {
                'flReplicaSpecs': {
                    'master': {
                        'template': {
                            'spec': {
                                'containers': [{
                                    'env': [{
                                        'name': 'CODE_KEY',
                                        'value': 'test-code-key'
                                    }]
                                }]
                            }
                        }
                    },
                    'worker': {
                        'template': {
                            'spec': {
                                'containers': [{
                                    'env': [{
                                        'name': 'CODE_TAR',
                                        'value': 'test-code-tar'
                                    }, {
                                        'name': 'EPOCH_NUM',
                                        'value': '3'
                                    }]
                                }]
                            }
                        }
                    }
                }
            }
        }
        flapp_envs = extract_flapp_envs(flapp_json)
        expected_flapp_envs = {
            'master': {
                'CODE_KEY': 'test-code-key'
            },
            'worker': {
                'CODE_TAR': 'test-code-tar',
                'EPOCH_NUM': '3'
            }
        }
        self.assertEqual(flapp_envs, expected_flapp_envs)

    def test_convert_built_in_functions(self):
        self.assertEqual(_to_int(''), None)
        self.assertEqual(_to_int('1.6'), 1)
        self.assertEqual(_to_float(''), None)
        self.assertEqual(_to_float('1.9'), 1.9)
        self.assertEqual(_to_bool('0'), False)
        self.assertEqual(_to_bool('false'), False)
        with self.assertRaises(ValueError):
            _to_dict('{}')
        with self.assertRaises(ValueError):
            _to_list('[]')
        self.assertEqual(_to_list([]), [])
        self.assertEqual(_to_dict({}), {})

    def test_eval_attribute_exception(self):
        with self.assertRaises(ValueError) as e:
            compile_yaml_template(yaml_template='a.b.c', post_processors=[], a={'b': 'd'})
        self.assertEqual(str(e.exception), 'Invalid python dict placeholder error msg: a.b.c')
        self.assertEqual(compile_yaml_template(yaml_template='a.b.c', post_processors=[], a={'b': {'c': 1}}), 1)

    def test_eval_syntax_exception(self):
        with self.assertRaises(ValueError) as e:
            compile_yaml_template(yaml_template='{,,}', post_processors=[], a={'b': 'd'})
        self.assertEqual(
            str(e.exception),
            """Invalid python dict syntax error msg: ('invalid syntax', ('<unknown>', 1, 2, '{,,}\\n'))""")

    def test_compile_yaml_template_ignore_variables(self):
        self.assertEqual(compile_yaml_template('jaweof', [], True), None)
        self.assertEqual(compile_yaml_template('{asdf: 12312, aaa:333}', [], True), {None: 333})
        self.assertEqual(compile_yaml_template('{asdf.a[1].b: 12312, "a": 3}', [], True), {None: 12312, 'a': 3})
        test_yaml_tpl = """
            {
              "apiVersion": "fedlearner.k8s.io/v1alpha1",
              "kind": "FLApp",
              "metadata": {
                "name": self.name,
                "namespace": system.variables.namespace,
                "labels": dict(system.variables.labels)
              },
                "containers": [
                  {
                    "env": system.basic_envs_list + [
                      {
                        "name": "EGRESS_HOST",
                        "value": project.participants[0].egress_host.lower()
                      },
                      {
                        "name": "OUTPUT_PARTITION_NUM",
                        "value": str(int(workflow.variables.partition_num))
                      },
                      {
                        "name": "OUTPUT_BASE_DIR",
                        "value": project.variables.storage_root_path + "/raw_data/" + self.name
                      },
                      {
                        "name": "RAW_DATA_METRICS_SAMPLE_RATE",
                        "value": str(asdfasdf)
                      }
                    ] + list(system.variables.volumes_list),
                  }
                ]
            }
        """
        self.assertEqual(compile_yaml_template(test_yaml_tpl, [], True).get('kind'), 'FLApp')


if __name__ == '__main__':
    unittest.main()

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

from google.protobuf.struct_pb2 import Value

from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition, WorkflowDefinition
from fedlearner_webconsole.utils.workflow import build_job_name, fill_variables, zip_workflow_variables


class UtilsTest(unittest.TestCase):

    def test_build_job_name(self):
        self.assertEqual(build_job_name('uuid', 'job_name'), 'uuid-job_name')

    def test_zip_workflow_variables(self):
        config = WorkflowDefinition(
            variables=[
                Variable(name='test',
                         value_type=Variable.ValueType.STRING,
                         typed_value=Value(string_value='test_value')),
                Variable(name='hello', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=1))
            ],
            job_definitions=[
                JobDefinition(variables=[
                    Variable(
                        name='hello_from_job', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=3))
                ])
            ])
        self.assertEqual(sum(1 for v in zip_workflow_variables(config)), 3)

    def test_fill_variables(self):
        config = WorkflowDefinition(
            variables=[
                Variable(name='test',
                         value_type=Variable.ValueType.STRING,
                         typed_value=Value(string_value='test_value')),
                Variable(name='hello', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=1))
            ],
            job_definitions=[
                JobDefinition(variables=[
                    Variable(
                        name='hello_from_job', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=3))
                ])
            ])
        variables = [
            Variable(name='test',
                     value_type=Variable.ValueType.STRING,
                     typed_value=Value(string_value='new_test_value'))
        ]
        config = fill_variables(config, variables)
        self.assertEqual(config.variables[0].typed_value.string_value, 'new_test_value')

    def test_fill_variables_invalid(self):
        config = WorkflowDefinition(
            variables=[
                Variable(name='test',
                         value_type=Variable.ValueType.STRING,
                         typed_value=Value(string_value='test_value')),
                Variable(name='hello', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=1))
            ],
            job_definitions=[
                JobDefinition(variables=[
                    Variable(
                        name='hello_from_job', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=3))
                ])
            ])
        variables = [Variable(name='test', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=2))]
        with self.assertRaises(TypeError):
            fill_variables(config, variables)

    def test_fill_variables_dry_run(self):
        config = WorkflowDefinition(
            variables=[
                Variable(name='test',
                         value_type=Variable.ValueType.STRING,
                         typed_value=Value(string_value='test_value')),
                Variable(name='hello', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=1))
            ],
            job_definitions=[
                JobDefinition(variables=[
                    Variable(
                        name='hello_from_job', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=3))
                ])
            ])
        variables = [
            Variable(name='test',
                     value_type=Variable.ValueType.STRING,
                     typed_value=Value(string_value='new_test_value'))
        ]
        config = fill_variables(config, variables, dry_run=True)
        self.assertEqual(config.variables[0].typed_value.string_value, 'test_value')


if __name__ == '__main__':
    unittest.main()

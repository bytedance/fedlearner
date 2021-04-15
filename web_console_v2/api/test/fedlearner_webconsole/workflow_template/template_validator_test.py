# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
from fedlearner_webconsole.workflow_template.template_validaor\
    import check_workflow_definition
from test_template_left import make_workflow_template


class TemplateValidatorTest(unittest.TestCase):


    def test_check_workflow_definition(self):
        workflow_definition = make_workflow_template()
        check_workflow_definition(workflow_definition)

    def test_check_more_json_wrong(self):
        yaml_template_more_comma = '{"a": "aa", "b":"" ,}'
        workflow_definition = make_workflow_template()
        workflow_definition.job_definitions[0].yaml_template = \
            yaml_template_more_comma
        with self.assertRaises(ValueError):
            check_workflow_definition(workflow_definition)

    def test_check_more_placeholder(self):
        workflow_definition = make_workflow_template()
        yaml_template_more_placeholder = '{"a": "${workflow.variables.nobody}"}'
        workflow_definition.job_definitions[0].yaml_template = \
            yaml_template_more_placeholder
        with self.assertRaises(ValueError):
            check_workflow_definition(workflow_definition)

    def test_check_wrong_placeholder(self):
        workflow_definition = make_workflow_template()
        yaml_template_wrong_placeholder = '{"a": "${workflow.xx!x.nobody}"}'
        workflow_definition.job_definitions[0].yaml_template =\
            yaml_template_wrong_placeholder
        with self.assertRaises(ValueError):
            check_workflow_definition(workflow_definition)


if __name__ == '__main__':
    unittest.main()

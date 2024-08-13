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

from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow_template.template_validaor\
    import check_workflow_definition
from testing.workflow_template.test_template_left import make_workflow_template
from testing.no_web_server_test_case import NoWebServerTestCase


class TemplateValidatorTest(NoWebServerTestCase):

    def test_check_workflow_definition(self):
        workflow_definition = make_workflow_template()
        with db.session_scope() as session:
            check_workflow_definition(workflow_definition, session)

    def test_check_more_json_wrong(self):
        yaml_template_more_comma = '{"a": "aa", "b": self.xxx}'
        workflow_definition = make_workflow_template()
        workflow_definition.job_definitions[0].yaml_template = \
            yaml_template_more_comma
        with db.session_scope() as session:
            with self.assertRaises(ValueError):
                check_workflow_definition(workflow_definition, session)

    def test_check_old_placeholder(self):
        workflow_definition = make_workflow_template()
        yaml_template_more_placeholder = '{"a": ${self.variables.batch_size}}'
        workflow_definition.job_definitions[0].yaml_template = \
            yaml_template_more_placeholder
        with db.session_scope() as session:
            with self.assertRaises(ValueError):
                check_workflow_definition(workflow_definition, session)

    def test_check_wrong_placeholder(self):
        workflow_definition = make_workflow_template()
        yaml_template_wrong_placeholder = '{"a": self.haha}'
        workflow_definition.job_definitions[0].yaml_template =\
            yaml_template_wrong_placeholder
        with db.session_scope() as session:
            with self.assertRaises(ValueError):
                check_workflow_definition(workflow_definition, session)


if __name__ == '__main__':
    unittest.main()

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

from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto import common_pb2, project_pb2
from testing.common import BaseTestCase


class ProjectTest(BaseTestCase):
    def test_get_namespace_fallback(self):
        project = Project()
        self.assertEqual(project.get_namespace(), 'default')

        project.set_config(project_pb2.Project(
            variables=[
                common_pb2.Variable(
                    name='test_name',
                    value='test_value'
                )
            ]
        ))
        self.assertEqual(project.get_namespace(), 'default')

    def test_get_namespace_from_variables(self):
        project = Project()
        project.set_config(project_pb2.Project(
            variables=[
                common_pb2.Variable(
                    name='namespace',
                    value='haha'
                )
            ]
        ))

        self.assertEqual(project.get_namespace(), 'haha')

if __name__ == '__main__':
    unittest.main()

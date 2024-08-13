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
from fedlearner_webconsole.iam.resource import ResourceType, is_valid_hierarchy, parse_resource_name


class ResourceTest(unittest.TestCase):

    def test_is_valid_hierarchy(self):
        self.assertTrue(is_valid_hierarchy(ResourceType.APPLICATION, ResourceType.PROJECT))
        self.assertTrue(is_valid_hierarchy(ResourceType.PROJECT, ResourceType.WORKFLOW))
        self.assertFalse(is_valid_hierarchy(ResourceType.DATASET, ResourceType.WORKFLOW))

    def test_parse_resource_name_correctly(self):
        resources = parse_resource_name('/')
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0].type, ResourceType.APPLICATION)
        self.assertEqual(resources[0].name, '/')
        resources = parse_resource_name('/projects/234234')
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].type, ResourceType.APPLICATION)
        self.assertEqual(resources[0].name, '/')
        self.assertEqual(resources[1].type, ResourceType.PROJECT)
        self.assertEqual(resources[1].name, '/projects/234234')
        self.assertEqual(resources[1].id, '234234')
        resources = parse_resource_name('/projects/123/workflows/333')
        self.assertEqual(len(resources), 3)
        self.assertEqual(resources[0].type, ResourceType.APPLICATION)
        self.assertEqual(resources[0].name, '/')
        self.assertEqual(resources[1].type, ResourceType.PROJECT)
        self.assertEqual(resources[1].name, '/projects/123')
        self.assertEqual(resources[1].id, '123')
        self.assertEqual(resources[2].type, ResourceType.WORKFLOW)
        self.assertEqual(resources[2].name, '/projects/123/workflows/333')
        self.assertEqual(resources[2].id, '333')
        resources = parse_resource_name('/projects/123/workflows')
        self.assertEqual(len(resources), 2)
        resources = parse_resource_name('/projects/123/workflows/2/peer_workflows')
        self.assertEqual(len(resources), 3)

    def test_parse_resource_name_invalid_hierarchy(self):
        with self.assertRaises(ValueError) as cm:
            parse_resource_name('/datasets/123/workflows/234')
        self.assertEqual(str(cm.exception), 'Invalid resource hierarchy')

    def test_parse_resource_name_invalid_string(self):
        with self.assertRaises(ValueError) as cm:
            parse_resource_name('/project/123')
        self.assertEqual(str(cm.exception), 'Invalid resource name')


if __name__ == '__main__':
    unittest.main()

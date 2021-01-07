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
import json
import unittest
from http import HTTPStatus

from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from testing.common import BaseTestCase


class WorkflowTemplatesApiTest(BaseTestCase):
    def get_config(self):
        config = super().get_config()
        config.START_GRPC_SERVER = False
        config.START_SCHEDULER = False
        return config

    def setUp(self):
        super().setUp()
        # Inserts data
        template1 = WorkflowTemplate(name='t1',
                                     comment='comment for t1',
                                     group_alias='g1')
        template1.set_config(WorkflowDefinition(
            group_alias='g1',
            is_left=True,
        ))
        template2 = WorkflowTemplate(name='t2',
                                     group_alias='g2')
        template2.set_config(WorkflowDefinition(
            group_alias='g2',
            is_left=False,
        ))
        db.session.add(template1)
        db.session.add(template2)
        db.session.commit()

    def test_get_with_group_alias(self):
        response = self.get_helper('/api/v2/workflow_templates?group_alias=g1')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.data).get('data')
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 't1')

    def test_get_all_templates(self):
        response = self.get_helper('/api/v2/workflow_templates')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.data).get('data')
        self.assertEqual(len(data), 2)

    def test_post_without_required_arguments(self):
        pass

    def test_post_successfully(self):
        template_name = 'test-nb-template'
        expected_template = WorkflowTemplate.query.filter_by(
            name=template_name).first()
        self.assertIsNone(expected_template)

        response = self.post_helper(
            '/api/v2/workflow_templates',
            data={
                'name': template_name,
                'comment': 'test-comment',
                'config': {
                    'group_alias': 'g222',
                    'is_left': True
                }
            })
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        data = json.loads(response.data).get('data')
        # Checks DB
        expected_template = WorkflowTemplate.query.filter_by(
            name=template_name).first()
        self.assertEqual(expected_template.name, template_name)
        self.assertEqual(expected_template.comment, 'test-comment')
        self.assertEqual(expected_template.config, WorkflowDefinition(
            group_alias='g222',
            is_left=True
        ).SerializeToString())
        self.assertEqual(data, expected_template.to_dict())


if __name__ == '__main__':
    unittest.main()

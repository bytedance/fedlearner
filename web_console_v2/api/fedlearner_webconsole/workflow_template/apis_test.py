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
import json
import unittest
import urllib.parse
from http import HTTPStatus
from unittest.mock import patch, MagicMock

from fedlearner_webconsole.db import db
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate, WorkflowTemplateKind, \
    WorkflowTemplateRevision
from fedlearner_webconsole.workflow_template.service import dict_to_workflow_definition
from testing.common import BaseTestCase


class WorkflowTemplatesApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        # Inserts data
        template1 = WorkflowTemplate(name='t1',
                                     comment='comment for t1',
                                     group_alias='g1',
                                     kind=WorkflowTemplateKind.DEFAULT.value)
        template1.set_config(WorkflowDefinition(group_alias='g1',))
        template2 = WorkflowTemplate(name='t2', group_alias='g2', kind=WorkflowTemplateKind.DEFAULT.value)
        template2.set_config(WorkflowDefinition(group_alias='g2',))
        with db.session_scope() as session:
            session.add(template1)
            session.add(template2)
            session.commit()

    def test_get_without_filter_and_pagination(self):
        response = self.get_helper('/api/v2/workflow_templates')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 20)

    def test_get_with_pagination(self):
        response = self.get_helper('/api/v2/workflow_templates?page=1&page_size=3')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 3)

    def test_get_with_invalid_filter(self):
        response = self.get_helper('/api/v2/workflow_templates?filter=invalid')
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_get_with_filter(self):
        filter_exp = urllib.parse.quote('(and(group_alias="g1")(name~="t")(kind=0))')
        response = self.get_helper(f'/api/v2/workflow_templates?filter={filter_exp}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.data).get('data')
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 't1')

    def test_get_with_kind(self):
        response = self.get_helper('/api/v2/workflow_templates?filter=%28kind%3D1%29')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        names = [t['name'] for t in data]
        self.assertTrue({
            'e2e-local',
            'sys-preset-nn-model',
            'sys-preset-tree-model',
            'e2e-fed-right',
            'e2e-fed-left',
            'e2e-sparse-estimator-test-right',
            'sys-preset-psi-data-join',
            'sys-preset-psi-data-join-analyzer',
        }.issubset(set(names)))

    def test_post_without_required_arguments(self):
        response = self.post_helper('/api/v2/workflow_templates', data={})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.data).get('details'),
            {'json': {
                'config': ['Missing data for required field.'],
                'name': ['Missing data for required field.']
            }})

        response = self.post_helper('/api/v2/workflow_templates',
                                    data={
                                        'name': 'test',
                                        'comment': 'test-comment',
                                        'config': {}
                                    })
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.data).get('details'), {'config.group_alias': 'config.group_alias is required'})

    def test_post_successfully(self):
        with db.session_scope() as session:
            template_name = 'test-nb-template'
            expected_template = session.query(WorkflowTemplate).filter_by(name=template_name).first()
            self.assertIsNone(expected_template)

        response = self.post_helper('/api/v2/workflow_templates',
                                    data={
                                        'name': template_name,
                                        'comment': 'test-comment',
                                        'config': {
                                            'group_alias': 'g222',
                                        },
                                        'kind': 1,
                                    })
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        data = json.loads(response.data).get('data')
        with db.session_scope() as session:
            # Checks DB
            expected_template = session.query(WorkflowTemplate).filter_by(name=template_name).first()
            self.assertEqual(expected_template.name, template_name)
            self.assertEqual(expected_template.comment, 'test-comment')
            self.assertEqual(expected_template.config, WorkflowDefinition(group_alias='g222').SerializeToString())
            expected_template_dict = {
                'comment': 'test-comment',
                'config': {
                    'group_alias': 'g222',
                    'job_definitions': [],
                    'variables': []
                },
                'editor_info': {
                    'yaml_editor_infos': {}
                },
                'group_alias': 'g222',
                'is_local': True,
                'name': 'test-nb-template',
                'kind': 1,
                'creator_username': 'ada',
                'coordinator_pure_domain_name': ''
            }
            self.assertPartiallyEqual(data, expected_template_dict, ignore_fields=['id', 'created_at', 'updated_at'])

    def test_delete_workflow_template(self):
        response = self.delete_helper('/api/v2/workflow_templates/1')
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        response = self.delete_helper('/api/v2/workflow_templates/1')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_put_workflow_template(self):
        with db.session_scope() as session:
            data = {'name': 'test_put', 'comment': 'test-comment', 'config': {'group_alias': 'g222'}}
            response = self.put_helper('/api/v2/workflow_templates/1', data=data)
            self.assertEqual(response.status_code, HTTPStatus.OK)
            expected_template = session.query(WorkflowTemplate).filter_by(id=1).first()
            self.assertEqual(expected_template.name, data['name'])
            self.assertEqual(expected_template.comment, data['comment'])
            self.assertEqual(expected_template.group_alias, data['config']['group_alias'])

    def test_dict_to_workflow_definition(self):
        config = {'variables': [{'name': 'code', 'value': '{"asdf.py": "asdf"}', 'value_type': 'CODE'}]}
        proto = dict_to_workflow_definition(config)
        self.assertTrue(isinstance(proto.variables[0].value, str))


class WorkflowTemplateApiTest(BaseTestCase):
    TEMPLATE1_ID = 10001

    def setUp(self):
        super().setUp()
        # Inserts data
        template1 = WorkflowTemplate(
            id=self.TEMPLATE1_ID,
            name='t1',
            comment='comment for t1 fff',
            group_alias='g1',
            kind=WorkflowTemplateKind.DEFAULT.value,
            creator_username='falin',
        )
        template1.set_config(WorkflowDefinition(group_alias='g1',))
        with db.session_scope() as session:
            session.add(template1)
            session.commit()

    def test_get(self):
        response = self.get_helper(f'/api/v2/workflow_templates/{self.TEMPLATE1_ID}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(
            response,
            {
                'id': self.TEMPLATE1_ID,
                'comment': 'comment for t1 fff',
                'name': 't1',
                'kind': 0,
                'creator_username': 'falin',
                'group_alias': 'g1',
                'is_local': True,
                'config': {
                    'group_alias': 'g1',
                    'job_definitions': [],
                    'variables': []
                },
                'editor_info': {
                    'yaml_editor_infos': {}
                },
                'coordinator_pure_domain_name': ''
            },
            ignore_fields=['created_at', 'updated_at'],
        )

    def test_download(self):
        response = self.get_helper(f'/api/v2/workflow_templates/{self.TEMPLATE1_ID}?download=true')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            json.loads(response.data.decode('utf-8')), {
                'comment': 'comment for t1 fff',
                'name': 't1',
                'group_alias': 'g1',
                'config': {
                    'group_alias': 'g1',
                    'job_definitions': [],
                    'variables': []
                },
                'editor_info': {
                    'yaml_editor_infos': {}
                },
            })


class WorkflowTemplateRevisionsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        # Inserts data
        with db.session_scope() as session:
            template1 = WorkflowTemplate(id=33,
                                         name='t1',
                                         comment='comment for t1',
                                         group_alias='g1',
                                         kind=WorkflowTemplateKind.DEFAULT.value)
            template1.set_config(WorkflowDefinition(group_alias='g1',))
            session.flush()
            self.template_rev1 = WorkflowTemplateRevision(template_id=template1.id,
                                                          config=template1.config,
                                                          revision_index=1)
            self.template_rev2 = WorkflowTemplateRevision(template_id=1, revision_index=1, config=template1.config)
            self.template_rev3 = WorkflowTemplateRevision(template_id=1, revision_index=2, config=template1.config)
            session.add(template1)
            session.add(self.template_rev1)
            session.add(self.template_rev2)
            session.add(self.template_rev3)
            session.commit()

    def test_get_revisions(self):
        response = self.get_helper('/api/v2/workflow_templates/1/workflow_template_revisions')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['revision_index'], 2)

    def test_get_revision(self):
        response = self.get_helper('/api/v2/workflow_template_revisions/1')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(data['config'], {'group_alias': 'g1', 'variables': [], 'job_definitions': []})
        response = self.get_helper('/api/v2/workflow_template_revisions/1?download=true')
        result = json.loads(response.data)
        self.assertEqual(
            result, {
                'revision_index': 1,
                'config': {
                    'group_alias': 'g1',
                    'variables': [],
                    'job_definitions': []
                },
                'editor_info': {
                    'yaml_editor_infos': {}
                },
                'name': 't1',
                'comment': ''
            })

    def test_create_revision(self):
        tpl_id = 33
        response = self.post_helper(f'/api/v2/workflow_templates/{tpl_id}:create_revision')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data1 = self.get_response_data(response)
        with db.session_scope() as session:
            tpl = session.query(WorkflowTemplate).get(tpl_id)
            tpl_config = to_dict(tpl.get_config())
        self.assertEqual(data1['revision_index'], 1)
        self.assertEqual(data1['template_id'], tpl_id)
        self.assertEqual(data1['config'], tpl_config)
        response = self.post_helper('/api/v2/workflow_templates/33:create_revision')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data2 = self.get_response_data(response)
        self.assertEqual(data1, data2)

    def test_delete_revision(self):
        response = self.delete_helper(f'/api/v2/workflow_template_revisions/{self.template_rev2.id}')
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        with db.session_scope() as session:
            self.assertEqual(session.query(WorkflowTemplateRevision).get(self.template_rev2.id), None)

    def test_delete_latest_revision(self):
        response = self.delete_helper(f'/api/v2/workflow_template_revisions/{self.template_rev3.id}')
        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)

    def test_patch_revision(self):
        response = self.patch_helper('/api/v2/workflow_template_revisions/1', data={'comment': 'test'})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(self.get_response_data(response)['comment'], 'test')
        with db.session_scope() as session:
            revision = session.query(WorkflowTemplateRevision).get(1)
            self.assertEqual(revision.comment, 'test')

    @patch('fedlearner_webconsole.workflow_template.apis.ProjectServiceClient.from_participant')
    def test_send_workflow_template_revision(self, mock_from_participant):
        with db.session_scope() as session:
            session.add(Participant(id=1, name='test', domain_name='test'))
            session.commit()
        mock_from_participant.return_value.send_template_revision = MagicMock()
        response = self.post_helper(
            f'/api/v2/workflow_template_revisions/{self.template_rev1.id}:send?participant_id=1')
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        mock_from_participant.return_value.send_template_revision.assert_called_once_with(
            config=self.template_rev1.get_config(),
            name='t1',
            comment=self.template_rev1.comment,
            kind=WorkflowTemplateKind.PEER,
            revision_index=self.template_rev1.revision_index)
        mock_from_participant.assert_called_once_with('test')


if __name__ == '__main__':
    unittest.main()

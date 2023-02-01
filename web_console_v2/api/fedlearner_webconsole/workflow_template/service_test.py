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

from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterExpressionKind, SimpleExpression, FilterOp
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate, WorkflowTemplateRevision, \
    WorkflowTemplateKind
from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow_template.service import WorkflowTemplateService, WorkflowTemplateRevisionService, \
    _check_config_and_editor_info
from fedlearner_webconsole.exceptions import NotFoundException, ResourceConflictException
from testing.no_web_server_test_case import NoWebServerTestCase


class WorkflowTemplateServiceTest(NoWebServerTestCase):

    def test_post_workflow_template(self):
        with db.session_scope() as session:
            data = {
                'name': 'test_template',
                'comment': 'test-comment-0',
                'config': {
                    'group_alias': 'g222',
                },
                'editor_info': {
                    'yaml_editor_infos': {}
                },
                'kind': 1,
                'creator_username': 'ada'
            }
            config, editor_info = _check_config_and_editor_info(config=data['config'], editor_info=data['editor_info'])
            template = WorkflowTemplateService(session).post_workflow_template(
                name=data['name'],
                comment=data['comment'],
                config=config,
                editor_info=editor_info,
                kind=data['kind'],
                creator_username=data['creator_username'])
            self.assertEqual(template.to_dict()['name'], data['name'])
            self.assertEqual(template.to_dict()['creator_username'], data['creator_username'])
            session.add(template)
            session.commit()
            conflict_data = {
                'name': 'test_template',
                'comment': 'test-comment-1',
                'config': {
                    'group_alias': 'g222',
                },
                'editor_info': {
                    'yaml_editor_infos': {}
                },
                'kind': 0,
            }
            config, editor_info = _check_config_and_editor_info(config=conflict_data['config'],
                                                                editor_info=conflict_data['editor_info'])
            with self.assertRaises(ResourceConflictException):
                WorkflowTemplateService(session).post_workflow_template(name=conflict_data['name'],
                                                                        comment=conflict_data['comment'],
                                                                        config=config,
                                                                        editor_info=editor_info,
                                                                        kind=conflict_data['kind'],
                                                                        creator_username='ada')

    def test_get_workflow_template(self):
        with db.session_scope() as session:
            config = WorkflowDefinition(group_alias='test_group_alias')
            template = WorkflowTemplate(name='test_template', group_alias=config.group_alias, kind=1)
            template.set_config(config)
            session.add(template)
            session.commit()

        with db.session_scope() as session:
            template = WorkflowTemplateService(session).get_workflow_template(name='test_template')
            self.assertEqual(template.get_config(), config)
            self.assertEqual(template.kind, 1)

        with db.session_scope() as session:
            with self.assertRaises(NotFoundException):
                WorkflowTemplateService(session).get_workflow_template(name='test_unexists_template')

    def test_list_workflow_templates(self):
        with db.session_scope() as session:
            t1 = WorkflowTemplate(id=145,
                                  name='test_template1',
                                  group_alias='group1',
                                  kind=WorkflowTemplateKind.PRESET.value,
                                  config=b'')
            t2 = WorkflowTemplate(id=146,
                                  name='test_template2',
                                  group_alias='group1',
                                  kind=WorkflowTemplateKind.PRESET.value,
                                  config=b'')
            t3 = WorkflowTemplate(id=147,
                                  name='hello',
                                  group_alias='group2',
                                  kind=WorkflowTemplateKind.DEFAULT.value,
                                  config=b'')
            session.add_all([t1, t2, t3])
            session.commit()
        with db.session_scope() as session:
            service = WorkflowTemplateService(session)
            # No filter and pagination
            pagination = service.list_workflow_templates()
            self.assertEqual(pagination.get_number_of_items(), 3)
            # Filter by name
            pagination = service.list_workflow_templates(
                filter_exp=FilterExpression(
                    kind=FilterExpressionKind.SIMPLE,
                    simple_exp=SimpleExpression(
                        field='name',
                        op=FilterOp.CONTAIN,
                        string_value='template',
                    ),
                ),
                page=1,
                page_size=1,
            )
            self.assertEqual(pagination.get_number_of_items(), 2)
            templates = pagination.get_items()
            self.assertEqual(len(templates), 1)
            self.assertEqual(templates[0].id, 146)
            # Filter by group alias and kind
            pagination = service.list_workflow_templates(
                filter_exp=FilterExpression(
                    kind=FilterExpressionKind.AND,
                    exps=[
                        FilterExpression(
                            kind=FilterExpressionKind.SIMPLE,
                            simple_exp=SimpleExpression(
                                field='group_alias',
                                op=FilterOp.EQUAL,
                                string_value='group1',
                            ),
                        ),
                        FilterExpression(
                            kind=FilterExpressionKind.SIMPLE,
                            simple_exp=SimpleExpression(
                                field='kind',
                                op=FilterOp.EQUAL,
                                number_value=WorkflowTemplateKind.PRESET.value,
                            ),
                        ),
                    ],
                ),
                page=1,
                page_size=10,
            )
            self.assertEqual(pagination.get_number_of_items(), 2)
            templates = pagination.get_items()
            self.assertEqual(len(templates), 2)
            self.assertEqual(templates[0].id, 146)
            self.assertEqual(templates[1].id, 145)


class WorkflowTemplateRevisionServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()

        with db.session_scope() as session:
            template = WorkflowTemplate(name='t1', comment='comment for t1', group_alias='g1')
            template.set_config(WorkflowDefinition(group_alias='g2',))
            session.add(template)
            session.commit()
            self.template_id = template.id

    def test_get_latest_revision(self):
        with db.session_scope() as session:
            for i in range(5):
                revision = WorkflowTemplateRevision(template_id=self.template_id, revision_index=i + 1, config=b'1')
                session.add(revision)
            session.commit()
        with db.session_scope() as session:
            self.assertEqual(
                WorkflowTemplateRevisionService(session).get_latest_revision(self.template_id).revision_index, 5)

    def test_create_new_revision_if_template_updated(self):
        with db.session_scope() as session:
            WorkflowTemplateRevisionService(session).create_new_revision_if_template_updated(self.template_id)
            WorkflowTemplateRevisionService(session).create_new_revision_if_template_updated(self.template_id)
            session.commit()
        with db.session_scope() as session:
            self.assertEqual(
                WorkflowTemplateRevisionService(session).get_latest_revision(self.template_id).revision_index, 1)
        with db.session_scope() as session:
            template = session.query(WorkflowTemplate).get(self.template_id)
            template.set_config(WorkflowDefinition(group_alias='g1',))
            session.commit()
        with db.session_scope() as session:
            WorkflowTemplateRevisionService(session).create_new_revision_if_template_updated(self.template_id)
            self.assertEqual(
                WorkflowTemplateRevisionService(session).get_latest_revision(self.template_id).revision_index, 2)

    def test_delete_revision(self):
        with db.session_scope() as session:
            revision_without_wf = WorkflowTemplateRevision(id=3,
                                                           template_id=self.template_id,
                                                           revision_index=1,
                                                           config=b'1')
            revision_with_wf = WorkflowTemplateRevision(id=4,
                                                        template_id=self.template_id,
                                                        revision_index=2,
                                                        config=b'1')
            workflow = Workflow(template_revision_id=revision_with_wf.id)
            revision_latest = WorkflowTemplateRevision(id=5,
                                                       template_id=self.template_id,
                                                       revision_index=3,
                                                       config=b'1')
            session.add_all([
                revision_without_wf,
                revision_with_wf,
                workflow,
                revision_latest,
            ])
            session.commit()
        with db.session_scope() as session:
            # OK to delete
            WorkflowTemplateRevisionService(session).delete_revision(3)
            with self.assertRaises(ResourceConflictException) as cm:
                WorkflowTemplateRevisionService(session).delete_revision(5)
            self.assertEqual(cm.exception.message, 'can not delete the latest_revision')
            with self.assertRaises(ResourceConflictException) as cm:
                WorkflowTemplateRevisionService(session).delete_revision(4)
            self.assertEqual(cm.exception.message, 'revision has been used by workflows')
            session.commit()
        with db.session_scope() as session:
            revisions = session.query(WorkflowTemplateRevision).filter_by(template_id=self.template_id).all()
            self.assertEqual(len(revisions), 2)
            self.assertEqual(revisions[0].id, revision_with_wf.id)
            self.assertEqual(revisions[1].id, revision_latest.id)

    def test_create_revision(self):
        with db.session_scope() as session:

            WorkflowTemplateRevisionService(session).create_revision(config=WorkflowDefinition(group_alias='test'),
                                                                     name='test',
                                                                     revision_index=2,
                                                                     comment='test comment',
                                                                     kind=WorkflowTemplateKind.PEER.name,
                                                                     peer_pure_domain='a')
            session.commit()
        with db.session_scope() as session:
            tpl = session.query(WorkflowTemplate).filter_by(name='test').first()
            self.assertEqual(tpl.coordinator_pure_domain_name, 'a')
            self.assertEqual(tpl.kind, 2)
            self.assertEqual(tpl.get_config(), WorkflowDefinition(group_alias='test'))
        with db.session_scope() as session:
            WorkflowTemplateRevisionService(session).create_revision(config=WorkflowDefinition(group_alias='test',
                                                                                               variables=[Variable()]),
                                                                     name='test',
                                                                     revision_index=3,
                                                                     comment='test comment',
                                                                     kind=WorkflowTemplateKind.PEER.name,
                                                                     peer_pure_domain='a')
            WorkflowTemplateRevisionService(session).create_revision(config=WorkflowDefinition(group_alias='test'),
                                                                     name='test',
                                                                     revision_index=1,
                                                                     comment='test comment',
                                                                     kind=WorkflowTemplateKind.PEER.name,
                                                                     peer_pure_domain='a')
            session.commit()
        with db.session_scope() as session:
            revisions = session.query(WorkflowTemplateRevision).filter_by(template_id=tpl.id).all()
            self.assertEqual(sorted([r.revision_index for r in revisions]), [1, 2, 3])
            tpl = session.query(WorkflowTemplate).filter_by(name='test').first()
            self.assertEqual(tpl.get_config(), WorkflowDefinition(group_alias='test', variables=[Variable()]))


if __name__ == '__main__':
    unittest.main()

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
from datetime import datetime, timezone

from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, \
    WorkflowTemplateEditorInfo
from fedlearner_webconsole.proto.workflow_template_pb2 import WorkflowTemplateRevisionRef, WorkflowTemplateRevisionPb, \
    WorkflowTemplatePb, WorkflowTemplateRef
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.workflow.models import Workflow  # pylint: disable=unused-import
from fedlearner_webconsole.workflow_template.models import WorkflowTemplateRevision, WorkflowTemplate, \
    WorkflowTemplateKind
from testing.no_web_server_test_case import NoWebServerTestCase


class WorkflowTemplateRevisionTest(NoWebServerTestCase):

    def test_to_revision_ref(self):
        created_at = datetime(2021, 10, 1, 8, 8, 8, tzinfo=timezone.utc)
        config = WorkflowDefinition().SerializeToString()
        template_revision = WorkflowTemplateRevision(id=123,
                                                     revision_index=1,
                                                     comment='a',
                                                     created_at=created_at,
                                                     config=config,
                                                     template_id=1)
        revision_ref = WorkflowTemplateRevisionRef(id=123,
                                                   revision_index=1,
                                                   comment='a',
                                                   template_id=1,
                                                   created_at=to_timestamp(created_at))
        self.assertEqual(template_revision.to_ref(), revision_ref)

    def test_to_workflow_proto(self):
        created_at = datetime(2021, 10, 1, 8, 8, 8, tzinfo=timezone.utc)
        config = WorkflowDefinition()
        template = WorkflowTemplate(name='test', id=1, group_alias='aa', config=b'')
        template_revision = WorkflowTemplateRevision(id=123,
                                                     revision_index=1,
                                                     comment='a',
                                                     created_at=created_at,
                                                     config=config.SerializeToString(),
                                                     template_id=1)
        revision_pb = WorkflowTemplateRevisionPb(id=123,
                                                 revision_index=1,
                                                 comment='a',
                                                 template_id=1,
                                                 created_at=to_timestamp(created_at),
                                                 config=config,
                                                 editor_info=WorkflowTemplateEditorInfo(),
                                                 is_local=True,
                                                 name='test')
        with db.session_scope() as session:
            session.add(template)
            session.add(template_revision)
            session.commit()
            self.assertEqual(template_revision.to_proto(), revision_pb)


class WorkflowTemplateTest(NoWebServerTestCase):

    def test_to_proto(self):
        created_at = datetime(2021, 10, 1, 8, 8, 8, tzinfo=timezone.utc)
        config = WorkflowDefinition()
        template = WorkflowTemplate(id=123,
                                    comment='a',
                                    created_at=created_at,
                                    config=config.SerializeToString(),
                                    updated_at=created_at,
                                    coordinator_pure_domain_name='test')
        tpl_pb = WorkflowTemplatePb(id=123,
                                    comment='a',
                                    created_at=to_timestamp(created_at),
                                    config=config,
                                    editor_info=WorkflowTemplateEditorInfo(),
                                    is_local=True,
                                    updated_at=to_timestamp(created_at),
                                    coordinator_pure_domain_name='test')
        self.assertEqual(template.to_proto(), tpl_pb)

    def test_to_ref(self):
        created_at = datetime(2021, 10, 1, 8, 8, 8, tzinfo=timezone.utc)
        config = WorkflowDefinition()
        template = WorkflowTemplate(id=123,
                                    comment='a',
                                    created_at=created_at,
                                    config=config.SerializeToString(),
                                    updated_at=created_at,
                                    coordinator_pure_domain_name='test',
                                    group_alias='test',
                                    kind=WorkflowTemplateKind.PEER.value)
        tpl_pb = WorkflowTemplateRef(id=123,
                                     comment='a',
                                     coordinator_pure_domain_name='test',
                                     group_alias='test',
                                     kind=WorkflowTemplateKind.PEER.value)
        self.assertEqual(template.to_ref(), tpl_pb)


if __name__ == '__main__':
    unittest.main()

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

# coding: utf-8

import unittest
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.paginate import paginate
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from testing.no_web_server_test_case import NoWebServerTestCase


def generate_workflow(state: WorkflowState = WorkflowState.RUNNING) -> Workflow:
    return Workflow(state=state)


class PaginateTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        workflows = [generate_workflow() for _ in range(7)]
        workflows += [generate_workflow(state=WorkflowState.INVALID) for _ in range(7)]

        with db.session_scope() as session:
            session.bulk_save_objects(workflows)
            session.commit()

    def test_paginate(self):
        with db.session_scope() as session:
            query = session.query(Workflow).filter(Workflow.state == WorkflowState.RUNNING)
            pagination = paginate(query, page=1, page_size=3)

            self.assertEqual(3, pagination.get_number_of_pages())
            self.assertEqual(3, len(pagination.get_items()))

            pagination = paginate(query, page=3, page_size=3)

            self.assertEqual(1, len(pagination.get_items()))

            pagination = paginate(query, page=4, page_size=3)

            self.assertEqual(0, len(pagination.get_items()))

    def test_page_meta(self):
        with db.session_scope() as session:
            query = session.query(Workflow)
            page_meta = paginate(query, page=1, page_size=3).get_metadata()
            self.assertDictEqual(page_meta, {'current_page': 1, 'page_size': 3, 'total_pages': 5, 'total_items': 14})

            query = session.query(Workflow).filter(Workflow.state == WorkflowState.RUNNING)
            page_meta = paginate(query, page=1, page_size=3).get_metadata()
            self.assertDictEqual(page_meta, {'current_page': 1, 'page_size': 3, 'total_pages': 3, 'total_items': 7})

            page_meta = paginate(query, page=4, page_size=10).get_metadata()
            self.assertDictEqual(page_meta, {'current_page': 4, 'page_size': 10, 'total_pages': 1, 'total_items': 7})

    def test_fallback_page_size(self):
        with db.session_scope() as session:
            query = session.query(Workflow).filter(Workflow.state == WorkflowState.RUNNING)
            pagination = paginate(query)

            self.assertEqual(7, len(pagination.get_items()))
            self.assertDictEqual(pagination.get_metadata(), {
                'current_page': 1,
                'page_size': 0,
                'total_pages': 1,
                'total_items': 7
            })


if __name__ == '__main__':
    unittest.main()

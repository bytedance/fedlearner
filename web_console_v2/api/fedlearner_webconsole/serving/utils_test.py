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

from fedlearner_webconsole.db import db
from fedlearner_webconsole.mmgr.models import Model
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.serving.utils import get_model
from testing.no_web_server_test_case import NoWebServerTestCase


class ServingServicesUtilsTest(NoWebServerTestCase):

    def setUp(self):
        self.maxDiff = None
        super().setUp()
        # insert project
        with db.session_scope() as session:
            project = Project()
            project.name = 'test_project_name'
            session.add(project)
            session.flush([project])

            model = Model()
            model.name = 'test_model_name'
            model.model_path = '/test_path/'
            model.group_id = 1
            model.uuid = 'test_uuid_1'
            model.project_id = project.id

            session.add(model)
            session.commit()
            self.project_id = project.id
            self.model_id = model.id
            self.model_uuid = model.uuid

    def test_get_model(self):
        with db.session_scope() as session:
            model = get_model(self.model_id, session)
        self.assertEqual(self.project_id, model.project_id)
        self.assertEqual(self.model_id, model.id)
        self.assertEqual(self.model_uuid, model.uuid)


if __name__ == '__main__':
    unittest.main()

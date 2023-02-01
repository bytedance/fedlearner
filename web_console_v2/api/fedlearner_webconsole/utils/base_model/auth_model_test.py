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
from testing.common import NoWebServerTestCase
from fedlearner_webconsole.utils.base_model.auth_model import AuthModel, AuthStatus
from fedlearner_webconsole.db import db, default_table_args


class TestModel(db.Model, AuthModel):
    __tablename__ = 'test_model'
    __table_args__ = (default_table_args('This is webconsole dataset table'))
    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)


class AuthModelTest(NoWebServerTestCase):

    def test_mixins(self):
        with db.session_scope() as session:
            model = TestModel(auth_status=AuthStatus.PENDING)
            session.add(model)
            session.commit()
        with db.session_scope() as session:
            models = session.query(TestModel).all()
            self.assertEqual(len(models), 1)
            self.assertEqual(models[0].auth_status, AuthStatus.PENDING)


if __name__ == '__main__':
    unittest.main()

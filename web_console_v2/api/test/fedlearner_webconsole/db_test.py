# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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

from datetime import datetime

from fedlearner_webconsole.db import db, to_dict_mixin
from fedlearner_webconsole.proto import common_pb2
from testing.common import create_test_db


@to_dict_mixin(ignores=['token', 'grpc_spec'], extras={
    'extra_key': (lambda model: model.get_grpc_spec())
})
class _TestModel(db.Model):
    __tablename__ = 'test_table'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255))
    token = db.Column('token_string', db.String(64), index=True,
                      key='token')
    created_at = db.Column(db.DateTime(timezone=True))
    grpc_spec = db.Column(db.Text())

    def set_grpc_spec(self, proto):
        self.grpc_spec = proto.SerializeToString()

    def get_grpc_spec(self):
        proto = common_pb2.GrpcSpec()
        proto.ParseFromString(self.grpc_spec)
        return proto


class DbTest(unittest.TestCase):
    def setUp(self):
        self._db = create_test_db()
        self._db.create_all()

    def tearDown(self):
        self._db.session.remove()
        self._db.drop_all()

    def test_to_dict_decorator(self):
        # 2020/12/17 13:58:59 UTC+8
        created_at_ts = 1608184739
        test_model = _TestModel(
            name='test-model',
            token='test-token',
            created_at=datetime.fromtimestamp(created_at_ts)
        )
        test_grpc_spec = common_pb2.GrpcSpec(egress_url='test-url', authority='test-authority')
        test_model.set_grpc_spec(test_grpc_spec)
        self._db.session.add(test_model)
        self._db.session.commit()

        models = _TestModel.query.all()
        self.assertEqual(len(models), 1)
        self.assertDictEqual(models[0].to_dict(), {
            'id': 1,
            'name': 'test-model',
            'created_at': created_at_ts,
            'extra_key': {
                'egress_url': 'test-url',
                'authority': 'test-authority',
                'extra_headers': {},
            }
        })


if __name__ == '__main__':
    unittest.main()

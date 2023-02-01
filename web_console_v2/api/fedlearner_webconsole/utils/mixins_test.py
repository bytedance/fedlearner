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
from datetime import datetime, timezone

from sqlalchemy.ext.declarative import declarative_base

from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.utils.mixins import to_dict_mixin

Base = declarative_base()


@to_dict_mixin(ignores=['token', 'grpc_spec'],
               extras={
                   'grpc_spec': lambda model: model.get_grpc_spec(),
                   'list': lambda _: ['hello', 'world']
               })
class DeclarativeClass(Base):
    __tablename__ = 'just_a_test'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    token = db.Column('token_string', db.String(64), index=True, key='token')
    updated_at = db.Column(db.DateTime(timezone=True))
    grpc_spec = db.Column(db.Text())

    def set_grpc_spec(self, proto):
        self.grpc_spec = proto.SerializeToString()

    def get_grpc_spec(self):
        proto = common_pb2.GrpcSpec()
        proto.ParseFromString(self.grpc_spec)
        return proto


@to_dict_mixin(to_dict_fields=['hhh'])
class SpecifyColumnsClass(object):

    def __init__(self) -> None:
        self.hhh = None
        self.not_include = None


class MixinsTest(unittest.TestCase):

    def test_to_dict_declarative_api(self):
        # 2021/04/23 10:42:01 UTC
        updated_at = datetime(2021, 4, 23, 10, 42, 1, tzinfo=timezone.utc)
        updated_at_ts = int(updated_at.timestamp())
        test_model = DeclarativeClass(id=123, name='test-model', token='test-token', updated_at=updated_at)
        test_grpc_spec = common_pb2.GrpcSpec(authority='test-authority')
        test_model.set_grpc_spec(test_grpc_spec)

        self.assertDictEqual(
            test_model.to_dict(), {
                'id': 123,
                'name': 'test-model',
                'updated_at': updated_at_ts,
                'grpc_spec': {
                    'authority': 'test-authority',
                },
                'list': ['hello', 'world']
            })

    def test_to_dict_specify_columns(self):
        obj = SpecifyColumnsClass()
        obj.hhh = 'hhh'
        res = obj.to_dict()
        self.assertEqual(len(res), 1)
        self.assertTrue('hhh' in res)


if __name__ == '__main__':
    unittest.main()

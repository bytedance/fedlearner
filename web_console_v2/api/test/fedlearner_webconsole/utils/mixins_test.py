# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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

from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base

from fedlearner_webconsole.utils.mixins import from_dict_mixin, to_dict_mixin

Base = declarative_base()


@to_dict_mixin()
class DeclarativeClass(Base):
    __tablename__ = 'just_a_test'

    test = Column(Integer, primary_key=True)


@to_dict_mixin(to_dict_fields=['hhh'])
@from_dict_mixin(from_dict_fields=['hhh'], required_fields=['hhh'])
class SpecifyColumnsClass(object):
    def __init__(self) -> None:
        self.hhh = None
        self.not_include = None


class MixinsTest(unittest.TestCase):
    def test_to_dict_declarative_api(self):
        obj = DeclarativeClass()
        res = obj.to_dict()
        self.assertEqual(len(res), 1)
        self.assertTrue('test' in res)

    def test_to_dict_specify_columns(self):
        obj = SpecifyColumnsClass()
        obj.hhh = 'hhh'
        res = obj.to_dict()
        self.assertEqual(len(res), 1)
        self.assertTrue('hhh' in res)

    def test_from_dict(self):
        inputs_pass = {'hhh': 4, 'hhhh': 1}
        inputs_raise = {'hhhh': 1}

        obj = SpecifyColumnsClass.from_dict(inputs_pass)
        self.assertEqual(obj.hhh, 4)
        with self.assertRaises(ValueError):
            obj = SpecifyColumnsClass.from_dict(inputs_raise)


if __name__ == '__main__':
    unittest.main()

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
from google.protobuf.struct_pb2 import Value, Struct

from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.workflow_template.utils import make_variable


class UtilsTest(unittest.TestCase):

    def test_make_variable(self):
        var = make_variable(name='haha', typed_value=None)
        self.assertEqual(var, Variable(name='haha'))
        var = make_variable(name='haha', typed_value=1.1)
        expected_var = Variable(name='haha',
                                value='1.1',
                                value_type=Variable.ValueType.NUMBER,
                                typed_value=Value(number_value=1.1))
        self.assertEqual(var, expected_var)
        var = make_variable(name='haha', typed_value='1')
        expected_var = Variable(name='haha',
                                value='1',
                                value_type=Variable.ValueType.STRING,
                                typed_value=Value(string_value='1'))
        self.assertEqual(var, expected_var)
        var = make_variable(name='haha', typed_value=True)
        expected_var = Variable(name='haha',
                                value='True',
                                value_type=Variable.ValueType.BOOL,
                                typed_value=Value(bool_value=True))
        self.assertEqual(var, expected_var)
        var = make_variable(name='haha', typed_value={'value': 1})
        typed_value = Struct()
        typed_value.update({'value': 1})
        expected_var = Variable(name='haha',
                                value='{"value": 1}',
                                value_type=Variable.ValueType.OBJECT,
                                typed_value=Value(struct_value=typed_value))
        self.assertEqual(var, expected_var)
        self.assertRaises(NotImplementedError, lambda: make_variable('haha', []))


if __name__ == '__main__':
    unittest.main()

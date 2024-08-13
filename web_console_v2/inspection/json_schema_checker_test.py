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

from json_schema_checker import SchemaChecker


class JsonSchemaCheckerTest(unittest.TestCase):

    def test_schema_check(self):
        json_schema = {
            'type': 'object',
            'properties': {
                'name': {
                    'type': 'string',
                },
                'age': {
                    'type': 'integer',
                },
                'father': {
                    'type': 'string',
                },
                'son': {
                    'type': 'null',
                },
                'is_student': {
                    'type': 'boolean',
                },
                'video': {
                    'type': 'string'
                }
            },
            'additionalProperties': False,
            'required': [
                'name',
                'age',
                'father',
                'son',
                'is_student',
            ]
        }
        checker = SchemaChecker(json_schema)

        data_1 = {
            'age': 10,
            'name': 'xiaoming',
            'father': 'old xiaoming',
            'son': None,
            'is_student': True,
            'video': bytearray([1, 2, 3]),
        }
        self.assertEqual(checker.check(data_1), [])

        data_2 = {
            'age': '10',
            'name': 'xiaoming',
            'father': 'old xiaoming',
            'mother': 'old xiaoming',
            'son': None,
            'video': b'test video',
        }
        error_msgs = [{
            'field': 'age',
            'message': '\'10\' is not of type \'integer\''
        }, {
            'field': '',
            'message': 'Additional properties are not allowed (\'mother\' was unexpected)'
        }, {
            'field': '',
            'message': '\'is_student\' is a required property'
        }]
        self.assertEqual(checker.check(data_2), error_msgs)

    def test_init_exception(self):
        json_schema_error_format = {'this is illegal format'}
        with self.assertRaises(RuntimeError):
            SchemaChecker(json_schema_error_format)


if __name__ == '__main__':
    unittest.main()

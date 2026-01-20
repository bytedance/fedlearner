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

from fedlearner_webconsole.utils.schema import spark_schema_to_json_schema


class SchemaConvertTest(unittest.TestCase):

    def test_spark_schema_to_json_schema(self):
        spark_schema = {
            'type':
                'struct',
            'fields': [{
                'name': 'raw_id',
                'type': 'integer',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'f01',
                'type': 'float',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'image',
                'type': 'binary',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'hight',
                'type': 'long',
                'nullable': True,
                'metadata': {}
            }]
        }

        json_schema = {
            'type': 'object',
            'properties': {
                'raw_id': {
                    'type': 'integer'
                },
                'f01': {
                    'type': 'number'
                },
                'image': {
                    'type': 'string'
                },
                'hight': {
                    'type': 'integer'
                }
            },
            'additionalProperties': False,
            'required': ['raw_id', 'f01', 'image', 'hight']
        }
        res = spark_schema_to_json_schema(spark_schema)
        self.assertEqual(res, json_schema)


if __name__ == '__main__':
    unittest.main()

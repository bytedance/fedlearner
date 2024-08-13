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

from typing import Optional

from fedlearner_webconsole.exceptions import InternalException

_SPARK_TO_JSON = {
    'integer': 'integer',
    'long': 'integer',
    'short': 'integer',
    'float': 'number',
    'double': 'number',
    'string': 'string',
    'binary': 'string',
    'boolean': 'boolean',
    'null': 'null',
}


def spark_schema_to_json_schema(spark_schema: Optional[dict]):
    """
    all fields in spark schema are deemed required in json schema
    any fields not in spark schema is deemed forbidden in json schema
    type convert from spark schema to json schema by _SPARK_TO_JSON
    Ref: https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.sql.types.StructField.html
    Ref: https://json-schema.org/learn/getting-started-step-by-step.html

    e.g.
    [from] spark schema:
    {
        'type': 'struct',
        'fields': [
            {
                'name': 'raw_id',
                'type': 'integer',
                'nullable': True,
                'metadata': {}
            },
            {
                'name': 'f01',
                'type': 'float',
                'nullable': True,
                'metadata': {}
            },
            {
                'name': 'image',
                'type': 'binary',
                'nullable': True,
                'metadata': {}
            }
        ]
    }

    [to] json schema:
    {
        'type': 'object',
        'properties':{
            'raw_id': {
                'type': 'integer'
            },
            'f01': {
                'type': 'number'
            },
            'image': {
                'type': 'string'
            }
        },
        'additionalProperties': False,
        'required': [
            'raw_id',
            'f01',
            'image'
        ]
    }
    """
    if spark_schema is None:
        return {}
    properties = {}
    required = []
    fields = spark_schema.get('fields')
    for field in fields:
        name = field.get('name')
        field_type = field.get('type')
        json_type = _SPARK_TO_JSON.get(field_type)
        if json_type is None:
            raise InternalException(
                f'spark schema to json schema convert failed! reason: unrecognized type [{field_type}]')
        properties[name] = {'type': json_type}
        required.append(name)
    json_schema = {'type': 'object', 'properties': properties, 'additionalProperties': False, 'required': required}
    return json_schema

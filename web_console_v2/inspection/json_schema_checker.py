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

from typing import Any, Dict, List
import logging

import jsonschema

_SCHEMA_CHECK_LOG = 'schema check'


class SchemaChecker(object):

    def __init__(self, schema: Dict[Any, Any]):
        self._schema = schema
        try:
            # spark broadcast use pickle serialization, cannot store draft7validator as a broadcast value
            jsonschema.Draft7Validator(self._schema)
        except Exception as e:  # pylint: disable=broad-except
            message = f'[{_SCHEMA_CHECK_LOG}] schema format error: schema format is invalid'
            logging.error(message)
            raise RuntimeError(message) from e

    def check(self, data: Dict) -> List[Dict[str, str]]:
        error_msgs = []
        # convert bytearray to string as json_schema only support string
        check_data = data.copy()
        for key, value in check_data.items():
            if isinstance(value, (bytes, bytearray)):
                check_data[key] = str(value)
        for error in jsonschema.Draft7Validator(self._schema).iter_errors(check_data):
            # TODO(lhh): schema check add example id to location row number
            error_msgs.append({'field': '.'.join(error.absolute_path), 'message': error.message})
        return error_msgs

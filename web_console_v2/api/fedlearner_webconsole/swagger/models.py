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

from typing import List

from marshmallow import Schema


class _SchemaManager(object):

    def __init__(self):
        self._schemas = []

    def append(self, schema: Schema):
        if schema in self._schemas:
            return
        self._schemas.append(schema)

    def get_schemas(self) -> List[Schema]:
        return self._schemas


schema_manager = _SchemaManager()

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
import json
from types import SimpleNamespace
from typing import Dict


def to_simple_namespace(x: Dict) -> SimpleNamespace:
    """A helper function to convert a dict to a SimpleNamespace.

    Sample usage:
    ```
        d = {'a': {'b': 123}}
        sn = to_simple_namespace(d)
        print(sn.a.b)
    ```
    """
    return json.loads(json.dumps(x), object_hook=lambda o: SimpleNamespace(**o))


class FakeResponse:

    def __init__(self, json_data, status_code, content=None, headers=None):
        self.json_data = json_data
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}

    def json(self):
        return self.json_data

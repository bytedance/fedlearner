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

# coding: utf-8
import json


class DatabaseFetcher:

    @staticmethod
    def fetch_by_int_key(query_key: int, signature: str) -> dict:
        result = {'raw_id': [query_key], 'example_id': [str(query_key)]}
        signature_dict = json.loads(signature)
        signature_input = signature_dict['inputs']
        for item in signature_input:
            input_name = item['name']
            input_type = item['type']
            result[input_name] = []
            if 'dim' in item:
                dim = int(item['dim'][0])
            else:
                dim = 1
            for _ in range(0, dim):
                # TODO(lixiaoguang.01) fetch from ABase, match name
                if input_type == 'DT_STRING':
                    result[input_name].append('')
                elif input_type in ('DT_FLOAT', 'DT_DOUBLE'):
                    result[input_name].append(0.1)
                elif input_type in ('DT_INT64', 'DT_INT32'):
                    result[input_name].append(1)
        return result

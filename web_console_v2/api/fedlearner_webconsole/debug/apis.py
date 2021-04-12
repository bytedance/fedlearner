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
from flask_restful import Resource, Api

from fedlearner_webconsole.composer.composer import composer
from fedlearner_webconsole.composer.runner import MemoryItem


class ComposerApi(Resource):
    def get(self, name):
        composer.collect(
            name,
            [MemoryItem(1), MemoryItem(2),
             MemoryItem(3)],
            {  # meta data
                1: {
                    'input': 'fs://data/memory_1',
                },
                2: {
                    'input': 'fs://data/memory_2',
                }
            })
        return {'code': '0', 'status': 'OK', 'data': {'name': name}}


def initialize_debug_apis(api: Api):
    api.add_resource(ComposerApi, '/debug/composer/<string:name>')

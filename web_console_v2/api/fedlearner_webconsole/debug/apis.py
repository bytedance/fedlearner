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
import json

from flask_restful import Resource, Api, request

from fedlearner_webconsole.composer.composer import composer
from fedlearner_webconsole.composer.runner import MemoryItem
from fedlearner_webconsole.dataset.data_pipeline import DataPipelineItem, \
    DataPipelineType


class ComposerApi(Resource):
    def get(self, name):
        interval = request.args.get('interval', -1)
        finish = request.args.get('finish', 0)
        if int(finish) == 1:
            composer.finish(name)
        else:
            composer.collect(
                name,
                [MemoryItem(1), MemoryItem(2)],
                {  # meta data
                    1: {
                        'input': 'fs://data/memory_1',
                    },
                    2: {
                        'input': 'fs://data/memory_2',
                    }
                },
                interval=int(interval),
            )
        return {'data': {'name': name}}


class DataPipelineApi(Resource):
    def get(self, name: str):
        # '/data/fl_v2_fish_fooding/dataset/20210527_221741_pipeline'
        input_dir = request.args.get('input_dir', None)
        if not input_dir:
            return {'msg': 'no input dir'}
        if 'pipe' in name:
            composer.collect(
                name,
                [DataPipelineItem(1), DataPipelineItem(2)],
                {  # meta data
                    1: {  # convertor
                        'sparkapp_name': '1',
                        'task_type': DataPipelineType.CONVERTER.value,
                        'input': [input_dir, 'batch/**/*.csv'],
                    },
                    2: {  # analyzer
                        'sparkapp_name': '2',
                        'task_type': DataPipelineType.ANALYZER.value,
                        'input': [input_dir, 'rds/**'],
                    },
                },
            )
        elif 'fe' in name:
            composer.collect(
                name,
                [DataPipelineItem(1)],
                {  # meta data
                    1: {  # transformer
                        'sparkapp_name': '1',
                        'task_type': DataPipelineType.TRANSFORMER.value,
                        'input': [input_dir, 'rds/**', json.dumps({
                            'f00000': 1.0,
                            'f00010': 0.0,
                        })],
                    },
                },
            )
        return {'data': {'name': name}}


def initialize_debug_apis(api: Api):
    api.add_resource(ComposerApi, '/debug/composer/<string:name>')
    api.add_resource(DataPipelineApi, '/debug/pipeline/<string:name>')

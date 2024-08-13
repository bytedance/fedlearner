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

from pathlib import Path

from fedlearner_webconsole.utils.swagger import remove_title, replace_ref_name, normalize_schema


class SwaggerTest(unittest.TestCase):

    def test_replace_ref_name(self):
        candidate = {
            '$ref': '#/definitions/no',
            'hello': {
                '$ref': '#/definitions/no',
                'world': {
                    '$ref': '#/definitions/no'
                }
            }
        }
        candidate = replace_ref_name(candidate, ref_name='yes', message_name='no')
        self.assertDictEqual(
            {
                '$ref': '#/definitions/yes',
                'hello': {
                    '$ref': '#/definitions/yes',
                    'world': {
                        '$ref': '#/definitions/yes'
                    }
                }
            }, candidate)

    def test_remove_title(self):
        candidate = {'title': 'hello', 'inner': {'title': 'world', 'inner': {'title': '!',}}}
        candidate = remove_title(candidate)
        self.assertDictEqual({'inner': {'inner': {}}}, candidate)

    def test_normalize_schema(self):
        candidate = {
            'FileTreeNode': {
                'properties': {
                    'files': {
                        'items': {
                            '$ref': '#/definitions/FileTreeNode'
                        },
                        'additionalProperties': False,
                        'type': 'array'
                    }
                },
                'additionalProperties': False,
                'type': 'object',
                'title': 'File Tree Node'
            }
        }

        candidate = normalize_schema(candidate, Path('aaa/FileTreeNode.json'))
        self.assertEqual(
            {
                # here
                'aaa.FileTreeNode': {
                    'properties': {
                        'files': {
                            'items': {
                                # here
                                '$ref': '#/definitions/aaa.FileTreeNode'
                            },
                            'additionalProperties': False,
                            'type': 'array'
                        }
                    },
                    'additionalProperties': False,
                    'type': 'object',
                    # no title
                }
            },
            candidate)

        candidate = {
            'AlgorithmData': {
                'properties': {
                    'version': {
                        '$ref': '#/definitions/AlgorithmData',
                    },
                    'parameter': {
                        '$ref': '#/definitions/fedlearner_webconsole.proto.AlgorithmParameter',
                        'additionalProperties': False
                    },
                },
                'additionalProperties': False,
                'type': 'object',
                'title': 'Algorithm Data'
            },
            'fedlearner_webconsole.proto.AlgorithmParameter': {
                'properties': {
                    'variables': {
                        'items': {
                            '$ref': '#/definitions/fedlearner_webconsole.proto.AlgorithmVariable'
                        },
                        'additionalProperties': False,
                        'type': 'array'
                    }
                },
                'additionalProperties': False,
                'type': 'object',
                'title': 'Algorithm Parameter'
            },
        }

        candidate = normalize_schema(candidate, Path('aaa/AlgorithmData.json'))
        self.assertDictEqual(
            {
                # here
                'aaa.AlgorithmData': {
                    'properties': {
                        'version': {
                            # here
                            '$ref': '#/definitions/aaa.AlgorithmData',
                        },
                        'parameter': {
                            # this does not change
                            '$ref': '#/definitions/fedlearner_webconsole.proto.AlgorithmParameter',
                            'additionalProperties': False
                        },
                    },
                    'additionalProperties': False,
                    'type': 'object',
                    # no title
                },
                'fedlearner_webconsole.proto.AlgorithmParameter': {
                    'properties': {
                        'variables': {
                            'items': {
                                # this does not change
                                '$ref': '#/definitions/fedlearner_webconsole.proto.AlgorithmVariable'
                            },
                            'additionalProperties': False,
                            'type': 'array'
                        }
                    },
                    'additionalProperties': False,
                    'type': 'object',
                    # no title
                }
            },
            candidate)


if __name__ == '__main__':
    unittest.main()

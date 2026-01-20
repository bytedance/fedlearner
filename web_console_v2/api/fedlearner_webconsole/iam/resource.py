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
# pylint: disable=redefined-builtin
import enum
import logging
import re
from typing import List


class ResourceType(enum.Enum):
    # Application level
    APPLICATION = 'application'
    PROJECT = 'projects'
    DATASET = 'datasets'
    WORKFLOW = 'workflows'


# yapf: disable
# Resource type hierarchies
_HIERARCHIES = [
    (ResourceType.APPLICATION, ResourceType.PROJECT),
    (ResourceType.PROJECT, ResourceType.DATASET),
    (ResourceType.PROJECT, ResourceType.WORKFLOW)
]
# yapf: enable


def is_valid_hierarchy(parent: ResourceType, child: ResourceType) -> bool:
    return (parent, child) in _HIERARCHIES


class Resource(object):

    def __init__(self, type: ResourceType, id: str, name: str):
        self.type = type
        self.id = id
        # Resource name, example: /projects/123/workflows/234
        self.name = name


_RESOURCE_PATTERN = re.compile(r'/([a-z]+)/([0-9]+)')


def parse_resource_name(name: str) -> List[Resource]:
    """Parses resource names to a list of resources.

    Why not using repeat groups in regex?
    Python does support this yet, so iterate the resources one by one in name.
    """
    resources = [Resource(ResourceType.APPLICATION, '', '/')]
    if name == '/':
        return resources
    last_match = 0
    normalized_name = ''
    for match in _RESOURCE_PATTERN.finditer(name):
        if match.start(0) != last_match:
            raise ValueError('Invalid resource name')
        last_match = match.end(0)
        try:
            r_type = ResourceType(match.group(1))
        except ValueError as e:
            logging.error(f'Unexpected resource type: {match.group(1)}')
            raise ValueError('Invalid resource name') from e
        id = match.group(2)
        normalized_name = f'{normalized_name}/{r_type.value}/{id}'
        resources.append(Resource(type=r_type, id=id, name=normalized_name))
    # ignore the resource suffix such as /peer_workflows, so the last match
    # may be not same as len(name).
    for i in range(1, len(resources)):
        if not is_valid_hierarchy(resources[i - 1].type, resources[i].type):
            raise ValueError('Invalid resource hierarchy')
    return resources

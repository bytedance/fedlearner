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
from typing import List, Union, Optional, Tuple

from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.iam.checker import checker
from fedlearner_webconsole.iam.permission import Permission, is_valid_binding
from fedlearner_webconsole.iam.resource import parse_resource_name, Resource, ResourceType
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.iam.permission import get_valid_permissions, \
    get_role_default_permissions


def check(username: str, resource_name: str, permission: Permission) -> bool:
    resources: List[Resource] = parse_resource_name(resource_name)
    # Checks bindings
    for resource in resources:
        if not is_valid_binding(resource.type, permission):
            raise ValueError(f'Invalid binding: {resource.type}-{permission}')
    for resource in resources:
        if checker.check(username, resource.name, permission):
            return True
    return False


def create_iams_for_resource(resource: Union[Project, Workflow], user: User):
    # Should not be used in grpc server.
    if isinstance(resource, Project):
        resource = f'/projects/{resource.id}'
        permissions = get_valid_permissions(ResourceType.PROJECT)
    else:
        return
    checker.create(user.username, resource, permissions)


def create_iams_for_user(user: User):
    checker.create(user.username, '/', get_role_default_permissions(user.role))


def get_iams(user: User, resource: Optional[str], permission: Optional[Permission]) -> List[Tuple[str, str, str]]:
    return [(item[0], item[1], item[2].value) for item in checker.get(user.username, resource, permission)]

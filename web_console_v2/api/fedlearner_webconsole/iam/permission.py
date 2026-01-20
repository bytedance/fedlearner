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
import enum
from typing import List
from fedlearner_webconsole.iam.resource import ResourceType
from fedlearner_webconsole.auth.models import Role


class Permission(enum.Enum):
    # Create project
    PROJECTS_POST = 'projects.post'
    PROJECT_GET = 'project.get'
    # Manage project
    PROJECT_PATCH = 'project.patch'
    # Create dataset
    DATASETS_POST = 'datasets.post'
    DATASET_DELETE = 'dataset.delete'
    # Create workflow
    WORKFLOWS_POST = 'workflows.post'
    # Config workflow
    WORKFLOW_PUT = 'workflow.put'
    # Update workflow
    WORKFLOW_PATCH = 'workflow.patch'


# Valid bindings between resources and permissions
_VALID_BINDINGS = [
    (ResourceType.APPLICATION, Permission.PROJECTS_POST),
    (ResourceType.APPLICATION, Permission.PROJECT_GET),
    (ResourceType.APPLICATION, Permission.PROJECT_PATCH),
    (ResourceType.APPLICATION, Permission.DATASETS_POST),
    (ResourceType.APPLICATION, Permission.DATASET_DELETE),
    (ResourceType.APPLICATION, Permission.WORKFLOWS_POST),
    (ResourceType.APPLICATION, Permission.WORKFLOW_PUT),
    (ResourceType.APPLICATION, Permission.WORKFLOW_PATCH),
    (ResourceType.PROJECT, Permission.PROJECT_GET),
    (ResourceType.PROJECT, Permission.PROJECT_PATCH),
    (ResourceType.PROJECT, Permission.DATASETS_POST),
    (ResourceType.PROJECT, Permission.DATASET_DELETE),
    (ResourceType.PROJECT, Permission.WORKFLOWS_POST),
    (ResourceType.PROJECT, Permission.WORKFLOW_PUT),
    (ResourceType.PROJECT, Permission.WORKFLOW_PATCH),
    (ResourceType.DATASET, Permission.DATASET_DELETE),
    (ResourceType.WORKFLOW, Permission.WORKFLOW_PUT),
    (ResourceType.WORKFLOW, Permission.WORKFLOW_PATCH),
]

_DEFAULT_PERMISSIONS = {
    Role.ADMIN: [
        Permission.PROJECTS_POST,
        Permission.PROJECT_GET,
        Permission.PROJECT_PATCH,
        Permission.DATASETS_POST,
        Permission.DATASET_DELETE,
        Permission.WORKFLOWS_POST,
        Permission.WORKFLOW_PUT,
        Permission.WORKFLOW_PATCH,
    ],
    Role.USER: [
        Permission.PROJECTS_POST,
        Permission.PROJECT_GET,
        Permission.DATASETS_POST,
        Permission.WORKFLOWS_POST,
        Permission.WORKFLOW_PUT,
    ]
}


def is_valid_binding(resource_type: ResourceType, permission: Permission) -> bool:
    return (resource_type, permission) in _VALID_BINDINGS


def get_valid_permissions(resource_type: ResourceType) -> List[Permission]:
    return [item[1] for item in _VALID_BINDINGS if item[0] == resource_type]


def get_role_default_permissions(user_role: Role) -> List[Permission]:
    # Because the enum in sqlalchemy could be any string, so we should defensive code as below.
    return _DEFAULT_PERMISSIONS.get(user_role, _DEFAULT_PERMISSIONS[Role.USER])

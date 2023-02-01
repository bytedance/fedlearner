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
from abc import ABCMeta, abstractmethod
from typing import List, Tuple, Optional

from envs import Envs
from fedlearner_webconsole.iam.permission import Permission


class IamChecker(metaclass=ABCMeta):

    @abstractmethod
    def check(self, identity: str, resource: str, permission: Permission) -> bool:
        pass

    @abstractmethod
    def create(self, identity: str, resource: str, permissions: List[Permission]):
        pass

    @abstractmethod
    def get(self, identity: str, resource: Optional[str],
            permission: Optional[Permission]) -> List[Tuple[str, str, Permission]]:
        pass


class ThirdPartyChecker(IamChecker):

    def check(self, identity: str, resource: str, permission: Permission) -> bool:
        # Calls API according to the configuration
        return True

    def create(self, identity: str, resource: str, permissions: List[Permission]):
        # Calls API according to the configuration
        return

    def get(self, identity: str, resource: Optional[str],
            permission: Optional[Permission]) -> List[Tuple[str, str, Permission]]:
        # Calls API according to the configuration
        pass


class TempChecker(IamChecker):

    def __init__(self):
        self.iams = []

    def check(self, identity: str, resource: str, permission: Permission) -> bool:
        # Calls API according to the configuration
        if Envs.FLASK_ENV == 'production':
            return True
        if (identity, resource, permission) in self.iams:
            return True
        return False

    def create(self, identity: str, resource: str, permissions: List[Permission]):
        # Calls API according to the configuration
        for permission in permissions:
            self.iams.append((identity, resource, permission))
        self.iams = list(set(self.iams))

    def get(self, identity: str, resource: Optional[str],
            permission: Optional[Permission]) -> List[Tuple[str, str, Permission]]:
        return [
            item for item in self.iams if item[0] == identity and resource is None or
            item[1] == resource and permission is None or item[2] == permission
        ]


checker: IamChecker = TempChecker()

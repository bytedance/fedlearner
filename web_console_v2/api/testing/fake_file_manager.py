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
from typing import List, Dict

from fedlearner_webconsole.utils.file_manager import FileManagerBase


class FakeFileManager(FileManagerBase):

    def can_handle(self, path: str) -> bool:
        return path.startswith('fake://')

    def ls(self, path: str, recursive=False, include_directory=False) -> List[Dict]:
        return [{'path': 'fake://data/f1.txt', 'size': 0}]

    def move(self, source: str, destination: str) -> bool:
        return source.startswith('fake://move')

    def remove(self, path: str) -> bool:
        return path.startswith('fake://remove')

    def copy(self, source: str, destination: str) -> bool:
        return source.startswith('fake://copy')

    def mkdir(self, path: str) -> bool:
        return path.startswith('fake://mkdir')

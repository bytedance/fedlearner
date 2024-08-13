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

from typing import List, Optional
from cityhash import CityHash64  # pylint: disable=no-name-in-module


class HashValueSet(object):

    def __init__(self) -> None:
        self._hash_map = {}

    def add_raw_values(self, values: List[str]):
        self._hash_map.update({str(CityHash64(value)): value for value in values})

    def get_raw_value(self, hashed_value: str) -> Optional[str]:
        try:
            return self._hash_map[hashed_value]
        except KeyError as e:
            raise Exception('Hashed value not found in hash map.') from e

    def get_hash_value_list(self) -> List[str]:
        return list(self._hash_map.keys())

    def exists(self, hashed_value: str) -> bool:
        return hashed_value in self._hash_map

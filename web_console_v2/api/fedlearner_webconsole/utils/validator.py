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

#  coding: utf-8
from typing import Callable, Optional, TypeVar, List, Dict, Union, Tuple, Any

T = TypeVar('T')


class Validator:

    def __init__(self, name: str, is_valid: Callable[[T], bool]):
        self.name = name
        self._is_valid = is_valid

    def is_valid(self, candidate: Optional[T]) -> Tuple[bool, Optional[str]]:
        if candidate is None:
            return False, f'"{self.name}" is required.'

        if not self._is_valid(candidate):
            return False, f'"{candidate}" is not a valid "{self.name}".'

        return True, None

    @staticmethod
    def validate(candidates: Dict[str, T],
                 validators: List['Validator']) -> Tuple[Union[bool, Any], List[Optional[str]]]:
        flag = True
        error_messages = []

        for validator in validators:
            passed, error_message = validator.is_valid(candidates.get(validator.name))
            flag = passed and flag
            if not passed:
                error_messages.append(error_message)

        return flag, error_messages

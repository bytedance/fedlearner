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
# pylint: disable=deprecated-class
from typing import Mapping
import six
from flatten_dict.flatten_dict import dot_reducer


def flatten(d):
    """
    Copied and modified from flatten_dict.flatten_dict, because the origin method
    convert {'a': {'b': 1}} to {'a.b': 1}, but we want {'a': {'b': 1}, 'a.b': 1}

    Flatten `Mapping` object.
    """
    flattenable_types = (Mapping,)
    if not isinstance(d, flattenable_types):
        raise ValueError(f'argument type {type(d)} is not in the flattenalbe types {flattenable_types}')

    reducer = dot_reducer
    flat_dict = {}

    def _flatten(d, parent=None):
        key_value_iterable = six.viewitems(d)
        for key, value in key_value_iterable:
            flat_key = reducer(parent, key)
            if isinstance(value, flattenable_types):
                flat_dict[flat_key] = value
                if value:
                    # recursively build the result
                    _flatten(value, flat_key)
                    continue
            flat_dict[flat_key] = value

    _flatten(d)
    return flat_dict

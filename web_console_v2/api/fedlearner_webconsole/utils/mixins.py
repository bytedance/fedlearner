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
from typing import List, Dict, Callable
from datetime import datetime
from enum import Enum

from sqlalchemy.ext.declarative import DeclarativeMeta

from google.protobuf.message import Message
from google.protobuf.json_format import MessageToDict

from fedlearner_webconsole.utils.pp_datetime import to_timestamp


def _to_dict_value(value):
    if isinstance(value, datetime):
        return to_timestamp(value)
    if isinstance(value, Message):
        return MessageToDict(value, preserving_proto_field_name=True, including_default_value_fields=True)
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, list):
        return [_to_dict_value(v) for v in value]
    if hasattr(value, 'to_dict'):
        return value.to_dict()
    return value


def to_dict_mixin(ignores: List[str] = None,
                  extras: Dict[str, Callable] = None,
                  to_dict_fields: List[str] = None,
                  ignore_none: bool = False):
    if ignores is None:
        ignores = []
    if extras is None:
        extras = {}
    if to_dict_fields is None:
        to_dict_fields = []

    def _get_fields(self: object) -> List[str]:
        if isinstance(self.__class__, DeclarativeMeta):
            return self.__table__.columns.keys()
        return to_dict_fields

    def decorator(cls):
        """A decorator to add a to_dict method to a class."""

        def to_dict(self: object):
            """A helper function to convert a class to dict."""
            dic = {}
            # Puts all columns into the dict
            for key in _get_fields(self):
                if key in ignores:
                    continue
                dic[key] = getattr(self, key)

            # Puts extra items specified by consumer
            for extra_key, func in extras.items():
                dic[extra_key] = func(self)
            # Converts type
            for key in dic:
                dic[key] = _to_dict_value(dic[key])

            # remove None and emtry list and dict
            if ignore_none:
                dic = {k: v for k, v in dic.items() if v}

            return dic

        setattr(cls, 'to_dict', to_dict)
        return cls

    return decorator

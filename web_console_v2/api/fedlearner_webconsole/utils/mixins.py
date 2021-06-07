# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy.ext.declarative import DeclarativeMeta

from google.protobuf.message import Message
from google.protobuf.json_format import MessageToDict


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
                value = dic[key]
                if isinstance(value, datetime):
                    # If there is no timezone, we should treat it as
                    # UTC datetime,otherwise it will be calculated
                    # as local time when converting to timestamp.
                    # Context: all datetime in db is UTC datetime,
                    # see details in config.py#turn_db_timezone_to_utc
                    if value.tzinfo is None:
                        dic[key] = int(
                            value.replace(tzinfo=timezone.utc).timestamp())
                    else:
                        dic[key] = int(value.timestamp())
                elif isinstance(value, Message):
                    dic[key] = MessageToDict(
                        value,
                        preserving_proto_field_name=True,
                        including_default_value_fields=True)
                elif isinstance(value, Enum):
                    dic[key] = value.name
                elif hasattr(value, 'to_dict'):
                    dic[key] = value.to_dict()

            # remove None and emtry list and dict
            if ignore_none:
                dic = {k: v for k, v in dic.items() if v}

            return dic

        setattr(cls, 'to_dict', to_dict)
        return cls

    return decorator


def from_dict_mixin(from_dict_fields: List[str] = None,
                    required_fields: List[str] = None):
    if from_dict_fields is None:
        from_dict_fields = []
    if required_fields is None:
        required_fields = []

    def decorator(cls: object):
        @classmethod
        def from_dict(cls: object, content: dict):
            obj = cls()  # pylint: disable=no-value-for-parameter
            for k in from_dict_fields:
                if k in content:
                    current_type = type(getattr(obj, k))
                    if hasattr(current_type, 'from_dict'):
                        setattr(obj, k, current_type.from_dict(content[k]))
                    else:
                        setattr(obj, k, content[k])
            for k in required_fields:
                if getattr(obj, k) is None:
                    raise ValueError(f'{type(obj)} should have attribute {k}')

            return obj

        setattr(cls, 'from_dict', from_dict)
        return cls

    return decorator

# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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

from enum import Enum
from datetime import datetime
from typing import List, Dict, Callable

from flask_sqlalchemy import SQLAlchemy
from google.protobuf.message import Message
from google.protobuf.json_format import MessageToDict

db = SQLAlchemy()


def to_dict_mixin(ignores: List[str] = None,
                  extras: Dict[str, Callable] = None):
    if ignores is None:
        ignores = []
    if extras is None:
        extras = {}

    def decorator(cls):
        """A decorator to add a to_dict method to a sqlalchemy model class."""
        def to_dict(self: db.Model):
            """A helper function to convert a sqlalchemy model to dict."""
            dic = {}
            # Puts all columns into the dict
            for col in self.__table__.columns:
                if col.name in ignores:
                    continue
                dic[col.name] = getattr(self, col.name)
            # Puts extra items specified by consumer
            for extra_key, func in extras.items():
                dic[extra_key] = func(self)
            # Converts type
            for key in dic:
                value = dic[key]
                if isinstance(value, datetime):
                    dic[key] = int(value.timestamp())
                elif isinstance(value, Message):
                    dic[key] = MessageToDict(
                        value,
                        preserving_proto_field_name=True,
                        including_default_value_fields=True)
                elif isinstance(value, Enum):
                    dic[key] = value.name
            return dic

        setattr(cls, 'to_dict', to_dict)
        return cls

    return decorator

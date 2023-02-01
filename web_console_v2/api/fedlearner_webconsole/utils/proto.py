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
import copy
from typing import Dict, Any

from google.protobuf import json_format
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from google.protobuf.struct_pb2 import Struct, Value

from fedlearner_webconsole.proto.common.extension_pb2 import secret


def _is_map(descriptor: FieldDescriptor) -> bool:
    """Checks if a field is map or normal repeated field.

    Inspired by https://github.com/protocolbuffers/protobuf/blob/3.6.x/python/google/protobuf/json_format.py#L159
    """
    return (descriptor.type == FieldDescriptor.TYPE_MESSAGE and descriptor.message_type.has_options and
            descriptor.message_type.GetOptions().map_entry)


def remove_secrets(proto: Message) -> Message:
    """Removes secrete fields in proto."""
    proto = copy.copy(proto)
    field: FieldDescriptor
    for field, value in proto.ListFields():
        if field.type != FieldDescriptor.TYPE_MESSAGE:
            # Clears field if it has secret annotation and its message is not message (no matter repeated or not)
            if field.GetOptions().Extensions[secret]:
                proto.ClearField(field.name)
            continue
        if field.label != FieldDescriptor.LABEL_REPEATED:
            # Nested message
            value.CopyFrom(remove_secrets(value))
            continue
        if _is_map(field):
            # Checks value type
            map_value_field: FieldDescriptor = field.message_type.fields_by_name['value']
            for k in list(value.keys()):
                if map_value_field.type == FieldDescriptor.TYPE_MESSAGE:
                    value[k].CopyFrom(remove_secrets(value[k]))
                else:
                    value[k] = map_value_field.default_value
        else:
            # Replace the repeated field (list of message)
            new_protos = [remove_secrets(m) for m in value]
            del value[:]
            value.extend(new_protos)

    return proto


_INT_TYPES = frozenset(
    [FieldDescriptor.TYPE_INT64, FieldDescriptor.TYPE_UINT64, FieldDescriptor.TYPE_INT32, FieldDescriptor.TYPE_UINT32])


def _normalize_singular(value: Any, proto_type: int) -> Any:
    if proto_type in _INT_TYPES:
        return int(value)
    return value


def _normalize_dict(dct: Dict, message: Message):
    """Normalizes the dict in place.

    Converts int64 type in dict to python int instead of string. Currently python
    proto lib will convert int64 to str, ref: https://github.com/protocolbuffers/protobuf/issues/2954

    So this is a hack to make the dict converting work as our expectation. If you do not want this
    behavior someday, you can use extension in the field case by case."""
    if isinstance(message, (Struct, Value)):
        # For those well-known protobuf types, we do not normalize it as
        # there are some magics.
        return
    descriptors = message.DESCRIPTOR.fields_by_name
    for key in dct:
        descriptor = descriptors.get(key)
        # Defensively
        if descriptor is None:
            continue
        # Repeated field
        if descriptor.label == FieldDescriptor.LABEL_REPEATED:
            nested = getattr(message, key)
            if _is_map(descriptor):
                # 1. Map
                map_key_type: FieldDescriptor = descriptor.message_type.fields_by_name['key'].type
                map_value_type: FieldDescriptor = descriptor.message_type.fields_by_name['value'].type
                for k, v in dct[key].items():
                    if map_value_type == FieldDescriptor.TYPE_MESSAGE:
                        # If type of key of mapper is int,
                        # we should convert it from string back to int for fetching information from Message
                        k = _normalize_singular(k, map_key_type)
                        _normalize_dict(v, nested[k])
                    else:
                        dct[key][k] = _normalize_singular(v, map_value_type)
            else:
                # 2. List
                for i, v in enumerate(dct[key]):
                    if descriptor.type == FieldDescriptor.TYPE_MESSAGE:
                        _normalize_dict(v, nested[i])
                    else:
                        dct[key][i] = _normalize_singular(v, descriptor.type)
            continue
        # Nested message
        if descriptor.type == FieldDescriptor.TYPE_MESSAGE:
            _normalize_dict(dct[key], getattr(message, key))
            continue
        # Singular field
        dct[key] = _normalize_singular(dct[key], descriptor.type)


def to_dict(proto: Message, with_secret: bool = True):
    if not with_secret:
        proto = remove_secrets(proto)
    dct = json_format.MessageToDict(proto, preserving_proto_field_name=True, including_default_value_fields=True)
    _normalize_dict(dct, proto)
    return dct


def to_json(proto: Message) -> str:
    """Converts proto to json string."""
    return json_format.MessageToJson(proto, preserving_proto_field_name=True)


def parse_from_json(json_str: str, proto: Message) -> Message:
    """Parses json string to a proto."""
    return json_format.Parse(json_str or '{}', proto, ignore_unknown_fields=True)

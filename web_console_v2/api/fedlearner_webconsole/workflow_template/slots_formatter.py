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
from string import Template
from typing import Dict

from fedlearner_webconsole.utils.pp_flatten_dict import flatten
from fedlearner_webconsole.proto.workflow_definition_pb2 import Slot
from fedlearner_webconsole.utils.proto import to_dict


class YamlTemplate(Template):
    """This formatter is used to format placeholders
    only can be observed in workflow_template module.
    """
    delimiter = '$'

    # overwrite this func to escape the invalid placeholder such as ${UNKNOWN}
    def _substitute(self, mapping, fixed_placeholder=None, ignore_invalid=False):
        # Helper function for .sub()
        def convert(mo):
            # Check the most common path first.
            named = mo.group('named') or mo.group('braced')
            if named is not None:
                if fixed_placeholder is not None:
                    return fixed_placeholder
                return str(mapping[named])
            if mo.group('escaped') is not None:
                return self.delimiter
            if mo.group('invalid') is not None:
                # overwrite to escape invalid placeholder
                if ignore_invalid:
                    return mo.group()
                self._invalid(mo)
            raise ValueError('Unrecognized named group in pattern', self.pattern)

        return self.pattern.sub(convert, self.template)


class _YamlTemplate(YamlTemplate):
    # Which placeholders in the template should be interpreted
    idpattern = r'Slot_[a-z0-9_]*'

    def substitute(self, mapping):
        return super()._substitute(mapping, fixed_placeholder=None, ignore_invalid=True)


def format_yaml(yaml, **kwargs):
    """Formats a yaml template.

    Example usage:
        format_yaml('{"abc": ${x.y}}', x={'y': 123})
    output should be  '{"abc": 123}'
    """
    template = _YamlTemplate(yaml)
    try:
        return template.substitute(flatten(kwargs or {}))
    except KeyError as e:
        raise RuntimeError(f'Unknown placeholder: {e.args[0]}') from e


def generate_yaml_template(base_yaml: str, slots_proto: Dict[str, Slot]):
    """
    Args:
        base_yaml: A string representation of one type job's base yaml.
        slots_proto: A proto map object representation of modification
        template's operable smallest units. Key is the slot name, and
        the value is Slot proto object.
    Returns:
        string: A yaml_template
    """
    slots = _generate_slots_map(slots_proto)
    return format_yaml(base_yaml, **slots)


def _generate_slots_map(slots_proto: dict) -> dict:
    slots = {}
    for key in slots_proto:
        slot = slots_proto[key]
        if slot.reference_type == Slot.DEFAULT:
            slots[key] = _generate_slot_default(slot)
        else:
            slots[key] = _generate_slot_reference(slot)
    return slots


def _generate_slot_default(slot: Slot):
    default_value = to_dict(slot.default_value)
    # add quotation for string value to make it be treated as string not a variable
    if slot.value_type == Slot.STRING:
        return f'"{default_value}"'
    if slot.value_type == Slot.INT:
        if default_value is None:
            return default_value
        try:
            return int(default_value)
        except Exception as e:
            raise ValueError(f'default_value of Slot: {slot.label} must be an int.') from e
    return default_value


def _generate_slot_reference(slot: Slot) -> str:
    if slot.value_type == Slot.INT:
        return f'int({slot.reference})'
    if slot.value_type == Slot.NUMBER:
        return f'float({slot.reference})'
    if slot.value_type == Slot.BOOL:
        return f'bool({slot.reference})'
    if slot.value_type == Slot.OBJECT:
        return f'dict({slot.reference})'
    if slot.value_type == Slot.LIST:
        return f'list({slot.reference})'
    # Force transform to string, to void format errors.
    if slot.value_type == Slot.STRING:
        return f'str({slot.reference})'
    return slot.reference

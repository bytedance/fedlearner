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
import re
from string import Formatter
import _string
_FIELD_RE = re.compile(r'\{([a-zA-Z_]+\.?)+\}')
class YamlFormatter(Formatter):
    # returns an iterable that contains tuples of the form:
    # (literal_text, field_name, format_spec, conversion)
    # literal_text can be zero length
    # field_name can be None, in which case there's no
    #  object to format and output
    # if field_name is not None, it is looked up, formatted
    #  with format_spec and conversion and then used
    def parse(self, s):
        last_stop_index = None
        for m in _FIELD_RE.finditer(s):
            token_name = m.group()[1:-1]
            start_index, stop_index = m.span()
            if start_index == 0:
                prefix_fragment = ''
            elif last_stop_index is None:
                prefix_fragment = s[:start_index]
            else:
                prefix_fragment = s[last_stop_index:start_index]
            last_stop_index = stop_index
            yield prefix_fragment, token_name, '', None
        yield s[last_stop_index:], None, None, None

    # given a field_name, find the object it references.
    #  field_name:   the field being looked up, e.g. "0.name"
    #                 or "lookup[3]"
    #  used_args:    a set of which args have been used
    #  args, kwargs: as passed in to vformat
    def get_field(self, field_name, args, kwargs):
        first, rest = _string.formatter_field_name_split(field_name)
        obj = self.get_value(first, args, kwargs)
        # loop through the rest of the field_name, doing
        #  getattr or getitem as needed
        for is_attr, i in rest:
            if is_attr:
                if hasattr(obj, i):
                    obj = getattr(obj, i)
                else:
                    if i == 'variables':
                        obj = obj.get_config().variables
                        continue
                    for item in obj:
                        if item.name == i:
                            obj = getattr(item, 'value') if hasattr(item, 'value') else item
                            break
            else:
                obj = obj[i]
        return obj, first

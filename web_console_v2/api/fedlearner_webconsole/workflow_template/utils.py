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

import json
from typing import Dict, Union
from google.protobuf.struct_pb2 import Value, Struct

from fedlearner_webconsole.proto.common_pb2 import Variable


def set_value(variable: Variable, typed_value: Union[None, str, int, float, bool, Dict]):
    if typed_value is None:
        return
    # since `isinstance(True, int)` is true, bool type should be placed before int type
    if isinstance(typed_value, bool):
        variable.value = str(typed_value)
        variable.value_type = Variable.ValueType.BOOL
        variable.typed_value.bool_value = typed_value
    elif isinstance(typed_value, (int, float)):
        variable.value = str(typed_value)
        variable.value_type = Variable.ValueType.NUMBER
        variable.typed_value.number_value = typed_value
    elif isinstance(typed_value, str):
        variable.value = typed_value
        variable.value_type = Variable.ValueType.STRING
        variable.typed_value.string_value = typed_value
    elif isinstance(typed_value, dict):
        variable.value = json.dumps(typed_value)
        variable.value_type = Variable.ValueType.OBJECT
        struct_var = Struct()
        struct_var.update(typed_value)
        variable.typed_value.MergeFrom(Value(struct_value=struct_var))
    else:
        raise NotImplementedError()


# TODO(xiangyuxuan): implement making variable from list typed_value
def make_variable(name: str, typed_value: Union[None, str, int, float, bool, Dict]) -> Variable:
    variable = Variable(name=name)
    set_value(variable, typed_value)
    return variable

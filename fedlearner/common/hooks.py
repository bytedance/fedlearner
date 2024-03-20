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
import os
import importlib
from typing import Any


def parse_and_call_fn(module_fn_path: str) -> Any:
    if module_fn_path.find(':') == -1:
        raise RuntimeError(f'Invalid module_fn_path: {module_fn_path}')

    module_path, func_name = module_fn_path.split(':')
    module = importlib.import_module(module_path)
    # Dynamically run the function
    return getattr(module, func_name)()


def pre_start_hook() -> Any:
    before_hook_path = os.getenv('PRE_START_HOOK', None)
    if before_hook_path:
        return parse_and_call_fn(before_hook_path)
    return None

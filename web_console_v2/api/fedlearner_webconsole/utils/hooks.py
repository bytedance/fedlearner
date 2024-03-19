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
import importlib
from typing import Any

from envs import Envs
from fedlearner_webconsole.db import db, get_database_uri
from fedlearner_webconsole.middleware.middlewares import flask_middlewares
from fedlearner_webconsole.middleware.request_id import FlaskRequestId
from fedlearner_webconsole.middleware.api_latency import api_latency_middleware


def parse_and_get_fn(module_fn_path: str) -> Any:
    if module_fn_path.find(':') == -1:
        raise RuntimeError(f'Invalid module_fn_path: {module_fn_path}')

    module_path, func_name = module_fn_path.split(':')
    try:
        module = importlib.import_module(module_path)
        fn = getattr(module, func_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise RuntimeError(f'Skipping run {module_fn_path} for no fn found') from e
    # Dynamically run the function
    return fn


def pre_start_hook():
    before_hook_path = Envs.PRE_START_HOOK
    if before_hook_path:
        parse_and_get_fn(before_hook_path)()

    # explicit rebind db engine to make hook work
    db.rebind(get_database_uri())

    # Applies middlewares
    flask_middlewares.register(FlaskRequestId())
    flask_middlewares.register(api_latency_middleware)

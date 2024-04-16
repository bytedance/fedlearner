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
import importlib

from envs import Envs
from fedlearner_webconsole.db import db_handler as db, get_database_uri


def pre_start_hook():
    before_hook_path = Envs.PRE_START_HOOK
    if before_hook_path:
        module_path, func_name = before_hook_path.split(':')
        module = importlib.import_module(module_path)
        # Dynamically run the function
        getattr(module, func_name)()

    # explicit rebind db engine to make hook work
    db.rebind(get_database_uri())

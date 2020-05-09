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

import pkgutil
import os
import inspect
import logging
import sys

from fedlearner.data_join.data_block_builder_impl.data_block_builder \
        import DataBlockBuilder

builder_impl_map = {}

__path__ = pkgutil.extend_path(__path__, __name__)
for _, module, ispackage in pkgutil.walk_packages(
        path=__path__, prefix=__name__+'.'):
    if ispackage:
        continue
    __import__(module)
    for _, m in inspect.getmembers(sys.modules[module], inspect.isclass):
        if not issubclass(m, DataBlockBuilder):
            continue
        builder_impl_map[m.name()] = m

def create_data_block_builder(options, *args, **kwargs):
    db_builder = options.data_block_builder
    if db_builder in builder_impl_map:
        return builder_impl_map[db_builder](*args, **kwargs)
    logging.fatal("Unknown data block builder %s", db_builder)
    os._exit(-1) # pylint: disable=protected-access
    return None

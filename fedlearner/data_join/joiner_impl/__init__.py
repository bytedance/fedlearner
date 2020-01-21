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

from fedlearner.data_join.joiner_impl.example_joiner import ExampleJoiner

from fedlearner.data_join.joiner_impl.stream_joiner import StreamExampleJoiner

joiner_impl_map = {}
default_joiner_impl = StreamExampleJoiner

__path__ = pkgutil.extend_path(__path__, __name__)
for _, module, ispackage in pkgutil.walk_packages(
        path=__path__, prefix=__name__+'.'):
    if ispackage:
        continue
    __import__(module)
    for _, m in inspect.getmembers(sys.modules[module], inspect.isclass):
        if not issubclass(m, ExampleJoiner):
            continue
        joiner_impl_map[m.name()] = m

def create_example_joiner(options, *args, **kwargs):
    joiner = options.get_example_joiner()
    if joiner is None:
        return default_joiner_impl(*args, **kwargs)
    if joiner in joiner_impl_map:
        return joiner_impl_map[joiner](*args, **kwargs)
    logging.fatal("Unknown example joiner %s", joiner)
    os._exit(-1) # pylint: disable=protected-access
    return None

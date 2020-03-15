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

import os
import pathlib
from configparser import ConfigParser


def get_fedlearner_home():
    return os.environ.get('FEDLEARNER_HOME',
                          '~/fedlearner')


def get_fedlearner_config(fedlearner_home):
    if 'FEDLEARNER_CONFIG' not in os.environ:
        return os.path.join(fedlearner_home, 'fedlearner.cfg')
    return os.environ['FEDLEARNER_CONFIG']


FEDLEARNER_HOME = get_fedlearner_home()
FEDLEARNER_CONFIG = get_fedlearner_config(FEDLEARNER_HOME)
pathlib.Path(FEDLEARNER_HOME).mkdir(parents=True, exist_ok=True)

conf = ConfigParser()
conf.read(FEDLEARNER_CONFIG)

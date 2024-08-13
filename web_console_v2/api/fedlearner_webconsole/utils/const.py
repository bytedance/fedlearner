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

# API
API_VERSION = '/api/v2'

# Pagination
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 50

# name of preset data join workflow template
SYS_DATA_JOIN_TEMPLATE = [
    # data join
    'sys-preset-data-join',
    'sys-preset-fe-data-join',
    # psi data join
    'sys-preset-psi-data-join',
    'sys-preset-fe-psi-data-join',
    # light client
    'sys-preset-light-psi-data-join',
    # TODO(xiangyuxuan.prs): change psi job type from TRANSFORMER to PSI_DATA_JOIN, when remove sys-preset-psi-data-join
    # psi data join with analyzer
    'sys-preset-psi-data-join-analyzer',
    'sys-preset-converter-analyzer'
]
# name of preset model workflow template
SYS_PRESET_VERTICAL_NN_TEMPLATE = 'sys-preset-nn-model'
SYS_PRESET_HORIZONTAL_NN_TEMPLATE = 'sys-preset-nn-horizontal-model'
SYS_PRESET_HORIZONTAL_NN_EVAL_TEMPLATE = 'sys-preset-nn-horizontal-eval-model'
SYS_PRESET_TREE_TEMPLATE = 'sys-preset-tree-model'

SYS_PRESET_TEMPLATE = [
    *SYS_DATA_JOIN_TEMPLATE, SYS_PRESET_VERTICAL_NN_TEMPLATE, SYS_PRESET_HORIZONTAL_NN_TEMPLATE,
    SYS_PRESET_HORIZONTAL_NN_EVAL_TEMPLATE, SYS_PRESET_TREE_TEMPLATE
]

# dataset
DATASET_PREVIEW_NUM = 20

DEFAULT_OWNER = 'no___user'

DEFAULT_OWNER_FOR_JOB_WITHOUT_WORKFLOW = 'no___workflow'

# auth related
SIGN_IN_INTERVAL_SECONDS = 1800
MAX_SIGN_IN_ATTEMPTS = 3

SYSTEM_WORKFLOW_CREATOR_USERNAME = 's_y_s_t_e_m'

SSO_HEADER = 'x-pc-auth'

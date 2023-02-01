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

import enum


class ExecutorType(enum.Enum):
    CRON_DATASET_JOB = 'CRON_DATASET_JOB'
    UPDATE_AUTH_STATUS = 'UPDATE_AUTH_STATUS'
    PENDING_DATASET_JOB_STAGE = 'PENDING_DATASET_JOB_STAGE'
    RUNNING_DATASET_JOB_STAGE = 'RUNNING_DATASET_JOB_STAGE'
    DATASET_JOB = 'DATASET_JOB'


class ExecutorResult(enum.Enum):
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'
    SKIP = 'SKIP'

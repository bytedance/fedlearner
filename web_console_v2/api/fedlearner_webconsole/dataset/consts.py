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

PLACEHOLDER = 'PLACEHOLDER'

CRON_SCHEDULER_FOLDER_NOT_READY_ERROR_MESSAGE = f'数据源下未找到满足格式要求的文件夹，请确认文件夹以{PLACEHOLDER}格式命名'
CRON_SCHEDULER_CERTAIN_FOLDER_NOT_READY_ERROR_MESSAGE = \
    f'{PLACEHOLDER}文件夹检查失败，请确认数据源下存在以{PLACEHOLDER}格式命名的文件夹，且文件夹下有_SUCCESS文件'
CRON_SCHEDULER_BATCH_NOT_READY_ERROR_MESSAGE = f'未找到满足格式要求的数据批次，请确保输入数据集有{PLACEHOLDER}格式命名的数据批次'
CRON_SCHEDULER_CERTAIN_BATCH_NOT_READY_ERROR_MESSAGE = f'数据批次{PLACEHOLDER}检查失败，请确认该批次命名格式及状态'
CRON_SCHEDULER_SUCCEEDED_MESSAGE = f'已成功发起{PLACEHOLDER}批次处理任务'

ERROR_BATCH_SIZE = -1
MANUFACTURER = 'dm9sY2VuZ2luZQ=='

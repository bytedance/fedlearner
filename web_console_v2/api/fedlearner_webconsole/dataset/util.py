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

# Functions in web_console_v2/inspection/util.py which used by webconsole
import os
from typing import Optional, Tuple
from envs import Envs
from slugify import slugify
from urllib.parse import urlparse
from datetime import datetime
import enum

from fedlearner_webconsole.dataset.consts import PLACEHOLDER, CRON_SCHEDULER_BATCH_NOT_READY_ERROR_MESSAGE, \
    CRON_SCHEDULER_CERTAIN_BATCH_NOT_READY_ERROR_MESSAGE, CRON_SCHEDULER_CERTAIN_FOLDER_NOT_READY_ERROR_MESSAGE, \
    CRON_SCHEDULER_FOLDER_NOT_READY_ERROR_MESSAGE, CRON_SCHEDULER_SUCCEEDED_MESSAGE
from fedlearner_webconsole.utils.file_manager import FileManager

DEFAULT_SCHEME_TYPE = 'file'


class CronInterval(enum.Enum):
    DAYS = 'DAYS'
    HOURS = 'HOURS'


def get_dataset_path(dataset_name: str, uuid: str):
    root_dir = add_default_url_scheme(Envs.STORAGE_ROOT)
    # Builds a path for dataset according to the dataset name
    # Example: '/data/dataset/xxxxxxxxxxxxx_test-dataset
    return f'{root_dir}/dataset/{uuid}_{slugify(dataset_name)[:32]}'


def get_export_dataset_name(index: int, input_dataset_name: str, input_data_batch_name: Optional[str] = None):
    if input_data_batch_name:
        return f'export-{input_dataset_name}-{input_data_batch_name}-{index}'
    return f'export-{input_dataset_name}-{index}'


def add_default_url_scheme(url: str) -> str:
    url_parser = urlparse(url)
    data_source_type = url_parser.scheme
    # set default source_type if no source_type found
    if data_source_type == '' and url.startswith('/'):
        url = f'{DEFAULT_SCHEME_TYPE}://{url}'
    return url


def _is_daily(file_name: str) -> bool:
    # YYYYMMDD format, like '20220701'
    # format must be YYYYMMDD, but time without zero padded like '202271' still could be recognized by strptime
    # so we force length of file_name must be 8
    # ref: https://docs.python.org/3.6/library/datetime.html#strftime-strptime-behavior
    if len(file_name) != 8:
        return False
    try:
        datetime.strptime(file_name, '%Y%m%d')
        return True
    except ValueError:
        return False


def _is_hourly(file_name: str) -> bool:
    # YYYYMMDD-HH format, like '20220701-01'
    # format must be YYYYMMDD-HH, but time without zero padded like '202271-1' still could be recognized by strptime
    # so we force length of file_name must be 11
    # ref: https://docs.python.org/3.6/library/datetime.html#strftime-strptime-behavior
    if len(file_name) != 11:
        return False
    try:
        datetime.strptime(file_name, '%Y%m%d-%H')
        return True
    except ValueError:
        return False


def is_streaming_folder(folder: str) -> Tuple[bool, str]:
    fm = FileManager()
    file_names = fm.listdir(folder)
    if len(file_names) == 0:
        return False, f'streaming data_path should contain folder with correct format, but path {folder} is empty'
    for file_name in file_names:
        if not fm.isdir(path=os.path.join(folder, file_name)):
            return False, f'data_source_url could only contains dir as subpath, {file_name} is not a dir'
        if not _is_daily(file_name) and not _is_hourly(file_name):
            return False, f'illegal dir format: {file_name}'
    return True, ''


def get_oldest_daily_folder_time(folder: str) -> Optional[datetime]:
    fm = FileManager()
    forder_names = fm.listdir(folder)
    oldest_folder_time = None
    for forder_name in forder_names:
        if not fm.isdir(path=os.path.join(folder, forder_name)):
            continue
        if _is_daily(forder_name):
            forder_time = datetime.strptime(forder_name, '%Y%m%d')
            if oldest_folder_time is None:
                oldest_folder_time = forder_time
            else:
                oldest_folder_time = min(oldest_folder_time, forder_time)
    return oldest_folder_time


def get_oldest_hourly_folder_time(folder: str) -> Optional[datetime]:
    fm = FileManager()
    forder_names = fm.listdir(folder)
    oldest_folder_time = None
    for forder_name in forder_names:
        if not fm.isdir(path=os.path.join(folder, forder_name)):
            continue
        if _is_hourly(forder_name):
            forder_time = datetime.strptime(forder_name, '%Y%m%d-%H')
            if oldest_folder_time is None:
                oldest_folder_time = forder_time
            else:
                oldest_folder_time = min(oldest_folder_time, forder_time)
    return oldest_folder_time


def parse_event_time_to_daily_folder_name(event_time: datetime) -> str:
    return event_time.strftime('%Y%m%d')


def parse_event_time_to_hourly_folder_name(event_time: datetime) -> str:
    return event_time.strftime('%Y%m%d-%H')


def check_batch_folder_ready(folder: str, batch_name: str) -> bool:
    batch_path = os.path.join(folder, batch_name)
    file_manager = FileManager()
    if not file_manager.isdir(batch_path):
        return False
    # TODO(liuhehan): add is_file func to file_manager and check is_file here
    if not file_manager.exists(os.path.join(batch_path, '_SUCCESS')):
        return False
    return True


# ====================================
# scheduler message funcs
# ====================================


def get_daily_folder_not_ready_err_msg() -> str:
    return CRON_SCHEDULER_FOLDER_NOT_READY_ERROR_MESSAGE.replace(PLACEHOLDER, 'YYYYMMDD')


def get_hourly_folder_not_ready_err_msg() -> str:
    return CRON_SCHEDULER_FOLDER_NOT_READY_ERROR_MESSAGE.replace(PLACEHOLDER, 'YYYYMMDD-HH')


def get_certain_folder_not_ready_err_msg(folder_name: str) -> str:
    return CRON_SCHEDULER_CERTAIN_FOLDER_NOT_READY_ERROR_MESSAGE.replace(PLACEHOLDER, folder_name)


def get_daily_batch_not_ready_err_msg() -> str:
    return CRON_SCHEDULER_BATCH_NOT_READY_ERROR_MESSAGE.replace(PLACEHOLDER, 'YYYYMMDD')


def get_hourly_batch_not_ready_err_msg() -> str:
    return CRON_SCHEDULER_BATCH_NOT_READY_ERROR_MESSAGE.replace(PLACEHOLDER, 'YYYYMMDD-HH')


def get_certain_batch_not_ready_err_msg(batch_name: str) -> str:
    return CRON_SCHEDULER_CERTAIN_BATCH_NOT_READY_ERROR_MESSAGE.replace(PLACEHOLDER, batch_name)


def get_cron_succeeded_msg(batch_name: str) -> str:
    return CRON_SCHEDULER_SUCCEEDED_MESSAGE.replace(PLACEHOLDER, batch_name)

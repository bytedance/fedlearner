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
import fsspec

import envs


@enum.unique
class AreaCode(enum.IntEnum):
    UNKNOWN = 0
    PARTITION = 1
    FEATURE_EXTRACTION = 2
    FORMAT_CHECKER = 3
    CONVERTER = 4
    ANALYZER = 5
    ALIGNMENT = 6
    PSI_OT = 7
    PSI_RSA = 8
    PSI_HASH = 9
    TRAINER = 10
    EXPORT_DATASET = 11


@enum.unique
class ErrorType(enum.IntEnum):
    # system error
    OUT_OF_MEMORY = 1
    CHANNEL_ERROR = 2
    # params error
    DATA_FORMAT_ERROR = 1001
    NO_KEY_COLUMN_ERROR = 1002
    DATA_NOT_FOUND = 1003
    DATA_LOAD_ERROR = 1004
    INPUT_PARAMS_ERROR = 1005
    DATA_WRITE_ERROR = 1006
    SCHEMA_CHECK_ERROR = 1007

    # other error
    RESULT_ERROR = 2001


def build_full_error_code(area_code: AreaCode, error_type: ErrorType) -> str:
    return str(area_code.value).zfill(4) + str(error_type.value).zfill(4)


class JobException(Exception):

    def __init__(self, area_code: AreaCode, error_type: ErrorType, message: str):
        super().__init__(message)
        self.area_code = area_code
        self.error_type = error_type
        self.message = message

    def __repr__(self):
        return f'{type(self).__name__}({build_full_error_code(self.area_code, self.error_type)}-{self.message})'

    def __str__(self) -> str:
        return f'{build_full_error_code(self.area_code, self.error_type)}-{self.message}'


def write_termination_message(area_code: AreaCode, error_type: ErrorType, error_message: str):
    error_code = build_full_error_code(area_code, error_type)
    termitation_message = f'{error_code}-{error_message}'
    with fsspec.open(envs.TERMINATION_LOG_PATH, 'w') as f:
        f.write(termitation_message)

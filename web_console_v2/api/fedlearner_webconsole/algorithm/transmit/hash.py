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

import hashlib

from fedlearner_webconsole.utils.file_manager import FileManager


def get_file_md5(file_manager: FileManager, file_name: str) -> str:
    # TODO(gezhengqiang): solve memory overflow problem
    data = file_manager.read(file_name).encode()
    return hashlib.md5(data).hexdigest()

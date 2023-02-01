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

import tempfile
from typing import Iterator, Optional
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.utils.file_operator import FileOperator
from fedlearner_webconsole.algorithm.transmit.hash import get_file_md5
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmData

file_operator = FileOperator()


class AlgorithmReceiver(object):

    def __init__(self):
        self._file_manager = FileManager()

    def write_data_and_extract(self,
                               data_iterator: Iterator[AlgorithmData],
                               dest: str,
                               expected_file_hash: Optional[str] = None):
        temp_dir = f'{dest}_temp'
        self._file_manager.mkdir(temp_dir)
        with tempfile.NamedTemporaryFile(suffix='.tar') as temp_file:
            # TODO: limit the size of the received file
            _written = False
            for data in data_iterator:
                self._file_manager.write(temp_file.name, data.chunk, mode='a')
                _written = True
            if _written:
                if expected_file_hash is not None:
                    file_hash = get_file_md5(self._file_manager, temp_file.name)
                    if file_hash != expected_file_hash:
                        raise ValueError('The received file is not completed')
                file_operator.extract_to(temp_file.name, temp_dir, create_dir=True)
        self._file_manager.rename(temp_dir, dest)

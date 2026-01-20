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
from io import BytesIO
from typing import Generator, Union
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.utils.file_operator import FileOperator
from fedlearner_webconsole.algorithm.transmit.hash import get_file_md5
from fedlearner_webconsole.proto.rpc.v2.resource_service_pb2 import GetAlgorithmFilesResponse

_DEFAULT_CHUNK_SIZE = 1024 * 1024
_FILE_MANAGER = FileManager()
_FILE_OPERATOR = FileOperator()


class AlgorithmSender(object):

    def __init__(self, chunk_size: int = _DEFAULT_CHUNK_SIZE):
        self.chunk_size = chunk_size

    def _file_content_generator(self, file: BytesIO) -> Generator[bytes, None, None]:
        while True:
            chunk = file.read(self.chunk_size)
            if len(chunk) == 0:
                return
            yield chunk

    def _archive_algorithm_files_into(self, algo_path: Union[str, None], dest_tar: str):
        if algo_path is None:
            return
        sources = [file.path for file in _FILE_MANAGER.ls(algo_path, include_directory=True)]
        if len(sources) > 0:
            _FILE_OPERATOR.archive_to(sources, dest_tar)

    def make_algorithm_iterator(self, algo_path: str) -> Generator[GetAlgorithmFilesResponse, None, None]:
        with tempfile.NamedTemporaryFile(suffix='.tar') as temp_file:
            self._archive_algorithm_files_into(algo_path, temp_file.name)
            file_hash = get_file_md5(_FILE_MANAGER, temp_file.name)
            chunk_generator = self._file_content_generator(temp_file.file)
            yield GetAlgorithmFilesResponse(hash=file_hash)
            for chunk in chunk_generator:
                yield GetAlgorithmFilesResponse(chunk=chunk)

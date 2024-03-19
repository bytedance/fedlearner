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

import os


class DatasetDirectory(object):
    """
    Dataset struct
    |
    |--- batch ---- batch_name_1 --- real data files
    |            |
    |            |- batch_name_2 --- real data files
    |            |
    |            |- batch_name_3 --- real data files
    |
    |--- meta   --- batch_name_1 --- thumbnails (only for image) --- preview image (.png)
    |            |                |
    |            |                |- _META
    |            |
    |            |- batch_name_2 --- thumbnails (only for image) --- preview image (.png)
    |            |                |
    |            |                |- _META
    |            |
    |            |- batch_name_3 --- thumbnails (only for image) --- preview image (.png)
    |            |                |
    |            |                |- _META
    |
    |--- errors --- batch_name_1 --- error message files (.csv)
    |            |
    |            |- batch_name_2 --- error message files (.csv)
    |            |
    |            |- batch_name_3 --- error message files (.csv)
    |
    |--- side_output --- batch_name_1 --- intermedia data
    |                 |
    |                 |- batch_name_2 --- intermedia data
    |                 |
    |                 |- batch_name_3 --- intermedia data
    |
    |--- _META (now move to meta/batch_name, delete in future)
    |
    |--- schema.json

    """
    _BATCH_DIR = 'batch'
    _META_DIR = 'meta'
    _ERRORS_DIR = 'errors'
    _SIDE_OUTPUT_DIR = 'side_output'
    _THUMBNAILS_DIR = 'thumbnails'
    _META_FILE = '_META'
    _SCHEMA_FILE = 'schema.json'
    _SOURCE_BATCH_PATH_FILE = 'source_batch_path'

    def __init__(self, dataset_path: str):
        self._dataset_path = dataset_path

    @property
    def dataset_path(self) -> str:
        return self._dataset_path

    def batch_path(self, batch_name: str) -> str:
        return os.path.join(self._dataset_path, self._BATCH_DIR, batch_name)

    def errors_path(self, batch_name: str) -> str:
        return os.path.join(self._dataset_path, self._ERRORS_DIR, batch_name)

    def thumbnails_path(self, batch_name: str) -> str:
        return os.path.join(self._dataset_path, self._META_DIR, batch_name, self._THUMBNAILS_DIR)

    def side_output_path(self, batch_name: str) -> str:
        return os.path.join(self._dataset_path, self._SIDE_OUTPUT_DIR, batch_name)

    def source_batch_path_file(self, batch_name: str) -> str:
        return os.path.join(self.batch_path(batch_name), self._SOURCE_BATCH_PATH_FILE)

    def batch_meta_file(self, batch_name) -> str:
        return os.path.join(self._dataset_path, self._META_DIR, batch_name, self._META_FILE)

    @property
    def schema_file(self) -> str:
        return os.path.join(self._dataset_path, self._SCHEMA_FILE)

    # TODO(liuhehan): remove it in future
    @property
    def meta_file(self) -> str:
        return os.path.join(self._dataset_path, self._META_FILE)

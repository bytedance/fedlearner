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

from fedlearner_webconsole.dataset.dataset_directory import DatasetDirectory
from fedlearner_webconsole.dataset.models import DataBatch, ImportType
from fedlearner_webconsole.utils.file_manager import FileManager


# we put this func out of data_batch model as this func will read file
def get_batch_data_path(data_batch: DataBatch):
    if data_batch.dataset.import_type == ImportType.NO_COPY:
        source_batch_path = DatasetDirectory(data_batch.dataset.path).source_batch_path_file(data_batch.batch_name)
        return FileManager().read(source_batch_path)
    return data_batch.path

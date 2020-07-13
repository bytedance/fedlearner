# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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

from fedlearner.data_join.csv_dict_writer import CsvDictWriter
from fedlearner.data_join.output_writer_impl.output_writer import OutputWriter

class CSVDictBuilder(OutputWriter):
    def __init__(self, options, fpath):
        super(CSVDictBuilder, self).__init__(options, fpath)
        self._writer = CsvDictWriter(fpath)

    def write_item(self, item):
        self._writer.write(item.csv_record)

    def close(self):
        self._writer.close()

    @classmethod
    def name(cls):
        return 'CSV_DICT'

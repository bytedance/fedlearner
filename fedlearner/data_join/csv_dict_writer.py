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

import csv

from tensorflow.compat.v1 import gfile

class CsvDictWriter(object):
    def __init__(self, fpath, headers=None):
        self._write_raw_num = 0
        self._fpath = fpath
        self._headers = [] if headers is None else headers
        self._header_set = set()
        self._fixed_header = headers
        self._file_hanlde = gfile.Open(fpath, 'w+')
        self._csv_writer = csv.DictWriter(
                self._file_hanlde,
                fieldnames=self._headers
            )

    def append_raw(self, raw):
        assert isinstance(raw, dict)
        if len(raw) == 0:
            return
        if not self._fixed_header:
            updated = False
            for key in raw.keys():
                if key not in self._header_set:
                    updated = True
                    self._headers.append(key)
                    self._header_set.add(key)
            if updated:
                self._csv_writer = csv.DictWriter(
                        self._file_hanlde,
                        fieldnames=self._headers
                    )
        self._csv_writer.writerow(raw)
        self._write_raw_num += 1

    def close(self):
        if self._file_hanlde is not None:
            if self._write_raw_num > 0:
                self._csv_writer.writeheader()
            self._file_hanlde.close()
            self._file_hanlde, self._csv_writer = None, None

    def write_raw_num(self):
        return self._write_raw_num

    def __del__(self):
        if self._file_hanlde is not None:
            self.close()

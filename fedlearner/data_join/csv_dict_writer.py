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
import io

import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile

class CsvDictWriter(object):
    def __init__(self, fpath):
        self._write_raw_num = 0
        self._fpath = fpath
        self._file_hanlde = gfile.Open(fpath, 'w+')
        self._buffer_handle = io.StringIO()
        self._csv_writer = None

    def write(self, raw):
        assert isinstance(raw, dict)
        if len(raw) == 0:
            return
        if self._csv_writer is None:
            self._csv_writer = csv.DictWriter(
                    self._buffer_handle,
                    fieldnames=raw.keys()
                )
            self._csv_writer.writeheader()
        # ignore the unnecessary fields
        diff = raw.keys() - self._csv_writer.fieldnames
        if diff:
            for k in diff:
                del raw[k]
        self._csv_writer.writerow(raw)
        self._write_raw_num += 1
        self._flush_buffer(False)

    def close(self):
        if self._buffer_handle is not None:
            self._flush_buffer(True)
            self._buffer_handle.close()
            self._buffer_handle = None
        if self._file_hanlde is not None:
            self._file_hanlde.close()
            self._file_hanlde = None
        self._csv_writer = None

    def write_raw_num(self):
        return self._write_raw_num

    def _flush_buffer(self, force=False):
        if self._buffer_handle.tell() > (8 << 20) or \
                (self._buffer_handle.tell() > 0 and force):
            self._file_hanlde.write(self._buffer_handle.getvalue())
            self._buffer_handle.truncate(0)
            self._buffer_handle.seek(0)

    def __del__(self):
        if self._file_hanlde is not None:
            self.close()

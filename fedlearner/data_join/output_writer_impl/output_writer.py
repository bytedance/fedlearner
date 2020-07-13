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


class OutputWriter(object):
    def __init__(self, options, fpath):
        self._options = options
        self._fpath = fpath
        self._output_cnt = 0

    def write_item(self, item):
        raise NotImplementedError("write not implement for basic OutputBuilder")

    def close(self):
        raise NotImplementedError("close not implement for basic OutputBuilder")

    @property
    def fpath(self):
        return self._fpath

    @classmethod
    def name(cls):
        return 'OUTPUT_BUILDER'

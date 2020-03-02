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

class DataBlock(object):
    def __init__(self, block_id, data_path, meta_path):
        self.block_id = block_id
        self.data_path = data_path
        self.meta_path = meta_path

    def validate(self):
        required_fields = ['block_id', 'data_path', 'meta_path']
        for field in required_fields:
            value = object.__getattribute__(self, field)
            if not value:
                raise Exception(
                    "illegal datablock missed field [{}].".format(field))
        return True

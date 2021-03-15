# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

import tarfile
from io import BytesIO
import base64
class CodeKeyParser(object):

    def encode(self, data_dict):
        # if data_dict is a dict ,
        # parse it to a tar file represented as base64 string
        assert isinstance(data_dict, dict)
        out = BytesIO()
        with tarfile.open(fileobj=out, mode='w:gz') as tar:
            for path in data_dict:
                tarinfo = tarfile.TarInfo(path)
                tarinfo.size = len(data_dict[path])
                tar.addfile(tarinfo, BytesIO(
                    data_dict[path].encode('utf-8')))
        result = str(base64.b64encode(out.getvalue()), encoding='utf-8')
        return f'base64://{result}'

    def decode(self, data_string):
        # if data_string is a tarfile ,
        # parse it to a dict that file path as keys
        code_dict = {}
        assert data_string.startswith('base64://')
        tar_binary = BytesIO(base64.b64decode(data_string[9:]))
        with tarfile.open(fileobj=tar_binary) as tar:
            for file in tar.getmembers():
                code_dict[file.name] = str(tar.extractfile(file).read(),
                                           encoding='utf-8')
        return code_dict






code_key_parser = CodeKeyParser()

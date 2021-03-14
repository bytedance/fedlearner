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
from fedlearner_webconsole.exceptions import InvalidArgumentException
class CodeKeyParser(object):

    def _encode(self, data_dict):
        # if data_dict is a dict ,
        # parse it to a tar file represented as base64 string
        if isinstance(data_dict, dict):
            out = BytesIO()
            with tarfile.open(fileobj=out, mode='w:gz') as tar:
                for path in data_dict:
                    tarinfo = tarfile.TarInfo(path)
                    tarinfo.size = len(data_dict[path])
                    tar.addfile(tarinfo, BytesIO(
                        data_dict[path].encode('utf-8')))
            result = str(base64.b64encode(out.getvalue()), encoding='utf-8')
            return result
        raise InvalidArgumentException('the values of code type'
                                       ' Variable must be a dict')

    def _decode(self, data_string):
        # if data_string is a tarfile ,
        # parse it to a dict that file path as keys
        tar_binary = BytesIO(base64.b64decode(data_string))
        code_dict = {}
        with tarfile.open(fileobj=tar_binary) as tar:
            for file in tar.getmembers():
                code_dict[file.name] = str(tar.extractfile(file).read(),
                                           encoding='utf-8')
        return code_dict

    def decode_code_key_in_config(self, config):
        if config is None:
            return None
        if 'variables' in config:
            for variable in config['variables']:
                # hard code only decode variable named code_key
                if variable['name'] == 'code_key':
                    variable['value'] = self._decode(variable['value'])
        if 'job_definitions' in config:
            for job in config['job_definitions']:
                if 'variables' in job:
                    for variable in job['variables']:
                        # hard code only decode variable named code_key
                        if variable['value_type'] == 'CODE':
                            variable['value'] = self._decode(
                                variable['value'])
        return config

    def encode_code_key_in_config(self, config):
        if config is None:
            return None
        if 'variables' in config:
            for variable in config['variables']:
                # hard code only decode variable named code_key
                if variable['name'] == 'code_key':
                    variable['value'] = self._encode(variable['value'])
        if 'job_definitions' in config:
            for job in config['job_definitions']:
                if 'variables' in job:
                    for variable in job['variables']:
                        # hard code only decode variable named code_key
                        if variable['value_type'] == 'CODE':
                            variable['value'] = self._encode(
                                variable['value'])
        return config


code_key_parser = CodeKeyParser()

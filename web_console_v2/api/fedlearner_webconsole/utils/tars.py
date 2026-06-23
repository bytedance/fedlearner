# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
import os
import tarfile


class TarCli:
    @staticmethod
    def _safe_target_path(extract_path_prefix, member_name):
        base_dir = os.path.realpath(extract_path_prefix)
        target_path = os.path.realpath(os.path.join(base_dir, member_name))
        if os.path.commonpath([base_dir, target_path]) != base_dir:
            raise ValueError(f'Unsafe tar member path: {member_name}')
        return target_path

    @staticmethod
    def untar_file(tar_name, extract_path_prefix):
        os.makedirs(extract_path_prefix, exist_ok=True)
        with tarfile.open(tar_name, 'r:*') as tar_pack:
            for member in tar_pack.getmembers():
                TarCli._safe_target_path(extract_path_prefix, member.name)
                if member.issym() or member.islnk():
                    TarCli._safe_target_path(extract_path_prefix, member.linkname)
                    continue
                tar_pack.extract(member, extract_path_prefix)

        return True

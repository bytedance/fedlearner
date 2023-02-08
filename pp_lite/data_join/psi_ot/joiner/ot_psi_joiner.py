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

import fsspec
import logging
import datetime
from enum import Enum
from typing import List

from pp_lite.data_join import envs
from pp_lite.proto.common_pb2 import DataJoinType
from pp_lite.data_join.psi_ot.joiner.joiner_interface import Joiner


def _write_ids(filename: str, ids: List[str]):
    with fsspec.open(filename, 'wt') as f:
        f.write('\n'.join(ids))


def _read_ids(filename: str) -> List[str]:
    with fsspec.open(filename, 'rt') as f:
        return f.read().splitlines()


class _Role(Enum):
    """the value is consistent with the argument of ot command"""
    client = 0  # psi sender; tcp client
    server = 1  # psi receiver; tcp server


def _timestamp() -> str:
    """Return string format of time to make test easier to mock"""
    return datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')


class OtPsiJoiner(Joiner):

    @property
    def type(self) -> DataJoinType:
        return DataJoinType.OT_PSI

    def _run(self, ids: List[str], role: _Role):
        timestamp = _timestamp()
        input_path = f'{envs.STORAGE_ROOT}/data/{role.name}-input-{timestamp}'
        output_path = f'{envs.STORAGE_ROOT}/data/{role.name}-output-{timestamp}'
        _write_ids(input_path, ids)
        # cmd = f'{CMD} -r {role.value} -file {input_path} -ofile {output_path}  && \
        # -ip localhost:{self.joiner_port}'.split()
        # logging.info(f'[OtPsiJoiner] run cmd: {cmd}')
        try:
            import psi_oprf  # pylint: disable=import-outside-toplevel
            psi_oprf.PsiRun(role.value, input_path, output_path, f'localhost:{self.joiner_port}')
            logging.info('[ot_psi_joiner] PsiRun finished.')
            # subprocess.run(cmd, check=True)
            joined_ids = _read_ids(output_path)
        except Exception as e:  # pylint: disable=broad-except
            logging.exception('[OtPsiJoiner] error happened during ot psi!')
            raise Exception from e
        finally:
            # delete the input and output file of ot program to release the storage volume
            fs = fsspec.get_mapper(input_path).fs
            fs.delete(input_path)
            if fs.exists(output_path):
                fs.delete(output_path)
        return joined_ids

    def client_run(self, ids: List[str]) -> List[str]:
        return self._run(ids, _Role.client)

    def server_run(self, ids: List[str]) -> List[str]:
        return self._run(ids, _Role.server)

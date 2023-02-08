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

import os
import shutil
import unittest
import tempfile
from concurrent.futures import ThreadPoolExecutor
import importlib.util as imutil

from pp_lite.data_join import envs
from pp_lite.proto.arguments_pb2 import Arguments
from pp_lite.proto.common_pb2 import DataJoinType
from pp_lite.data_join.psi_ot.client import run as client_run
from pp_lite.data_join.psi_ot.server import run as server_run
from pp_lite.testing.make_data import make_data


def check_psi_oprf():
    spec = imutil.find_spec('psi_oprf')
    if spec is None:
        psi_oprf_existed = False
    else:
        psi_oprf_existed = True
    return psi_oprf_existed


class IntegratedTest(unittest.TestCase):

    _PART_NUM = 2

    def setUp(self) -> None:
        self._temp_dir = tempfile.mkdtemp()
        envs.STORAGE_ROOT = self._temp_dir
        self._client_input_path = os.path.join(self._temp_dir, 'client')
        self._server_input_path = os.path.join(self._temp_dir, 'server')
        self._client_output_path = os.path.join(self._temp_dir, 'client_output')
        self._server_output_path = os.path.join(self._temp_dir, 'server_output')
        make_data(self._PART_NUM, self._client_input_path, self._server_input_path)

    def tearDown(self) -> None:
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    def _run_client(self, data_join_type: DataJoinType):
        args = Arguments(input_path=self._client_input_path,
                         output_path=self._client_output_path,
                         key_column='raw_id',
                         data_join_type=data_join_type,
                         server_port=50051,
                         joiner_port=50053,
                         worker_rank=0,
                         num_workers=1,
                         partitioned=True)
        args.cluster_spec.workers.extend(['worker-0'])
        client_run(args)

    def _run_server(self, data_join_type: DataJoinType):
        args = Arguments(input_path=self._server_input_path,
                         output_path=self._server_output_path,
                         key_column='raw_id',
                         data_join_type=data_join_type,
                         server_port=50051,
                         joiner_port=50053,
                         worker_rank=0)
        args.cluster_spec.workers.extend(['worker-0'])
        server_run(args)

    def _run(self, data_join_type: DataJoinType):
        pool = ThreadPoolExecutor(max_workers=2)
        pool.submit(self._run_server, data_join_type)
        self._run_client(data_join_type)
        pool.shutdown()
        # success tags are included
        self.assertEqual(len(os.listdir(self._client_output_path)), self._PART_NUM * 2)
        self.assertEqual(len(os.listdir(self._server_output_path)), self._PART_NUM * 2)

    def test_run_hashed_data_join(self):
        self._run(DataJoinType.HASHED_DATA_JOIN)

    @unittest.skipUnless(check_psi_oprf(), 'require ot psi file')
    def test_ot_psi(self):
        self._run(DataJoinType.OT_PSI)


if __name__ == '__main__':
    unittest.main()

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

import unittest
from typing import List
from unittest.mock import patch
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
import importlib.util as imutil

from pp_lite.data_join import envs
from pp_lite.data_join.psi_ot.joiner.ot_psi_joiner import OtPsiJoiner


def _write_fake_output(filename: str, ids: List[str]):
    with open(filename, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(ids))


def check_psi_oprf():
    spec = imutil.find_spec('psi_oprf')
    if spec is None:
        psi_oprf_existed = False
    else:
        psi_oprf_existed = True
    return psi_oprf_existed


@unittest.skipUnless(check_psi_oprf(), 'require ot psi file')
class OtPsiJoinerTest(unittest.TestCase):

    @patch('pp_lite.data_join.psi_ot.joiner.ot_psi_joiner._timestamp')
    def test_client_run(self, mock_run, mock_timestamp):
        joiner = OtPsiJoiner(joiner_port=12345)
        timestamp = '20220310-185545'
        mock_timestamp.return_value = timestamp
        with TemporaryDirectory() as temp_dir:
            envs.STORAGE_ROOT = temp_dir
            input_path = f'{envs.STORAGE_ROOT}/data/client-input-{timestamp}'
            output_path = f'{envs.STORAGE_ROOT}/data/client-output-{timestamp}'
            inter_ids = ['4', '5', '6']

            def _side_effect(*args, **kwargs):
                _write_fake_output(output_path, inter_ids)

            mock_run.side_effect = _side_effect
            ids = joiner.client_run(['1', '2', '3'])
            mock_run.assert_called_with(0, input_path, output_path, f'localhost:{self.joiner_port}')
            self.assertEqual(ids, inter_ids)

    @patch('pp_lite.data_join.psi_ot.joiner.ot_psi_joiner._timestamp')
    def test_server_run(self, mock_run, mock_timestamp):
        joiner = OtPsiJoiner(joiner_port=12345)
        timestamp = '20220310-185545'
        mock_timestamp.return_value = timestamp
        with TemporaryDirectory() as temp_dir:
            envs.STORAGE_ROOT = temp_dir
            input_path = f'{envs.STORAGE_ROOT}/data/server-input-{timestamp}'
            output_path = f'{envs.STORAGE_ROOT}/data/server-output-{timestamp}'
            inter_ids = ['4', '5', '6']

            def _side_effect(*args, **kwargs):
                _write_fake_output(output_path, inter_ids)

            mock_run.side_effect = _side_effect
            ids = joiner.server_run(['1', '2', '3'])
            mock_run.assert_called_with(1, input_path, output_path, f'localhost:{self.joiner_port}')
            self.assertEqual(ids, inter_ids)


@unittest.skipUnless(check_psi_oprf(), 'require ot psi file')
class OtPsiJoinerInContainerTest(unittest.TestCase):

    def test_joiner(self):
        client_ids = [str(i) for i in range(10000)]
        server_ids = [str(i) for i in range(5000, 15000)]
        joined_ids = [str(i) for i in range(5000, 10000)]
        joiner = OtPsiJoiner(joiner_port=1212)
        with ThreadPoolExecutor(max_workers=2) as pool:
            client_fut = pool.submit(joiner.client_run, client_ids)
            server_fut = pool.submit(joiner.server_run, server_ids)
            client_result = client_fut.result()
            server_result = server_fut.result()
            self.assertEqual(client_result, server_result)
            self.assertEqual(sorted(client_result), joined_ids)


if __name__ == '__main__':
    unittest.main()

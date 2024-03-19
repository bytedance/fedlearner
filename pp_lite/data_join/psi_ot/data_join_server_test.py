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
import time
import shutil
import tempfile
import unittest
from typing import List, Optional

from pp_lite.proto.common_pb2 import FileType, DataJoinType
from pp_lite.data_join.psi_ot.data_join_server import DataJoinServer
from pp_lite.data_join.psi_ot.joiner.joiner_interface import Joiner
from pp_lite.data_join.utils.example_id_reader import ExampleIdReader
from pp_lite.data_join.utils.example_id_writer import ExampleIdWriter
from pp_lite.testing.make_data import _make_fake_data


class TestJoiner(Joiner):

    def __init__(self, wait_time: Optional[float] = None):
        super().__init__(12345)
        self._wait_time = wait_time

    @property
    def type(self) -> DataJoinType:
        return DataJoinType.HASHED_DATA_JOIN

    def client_run(self, ids: List[str]) -> List[str]:
        return []

    def server_run(self, ids: List[str]) -> List[str]:
        if self._wait_time:
            time.sleep(self._wait_time)
        return ids


class DataJoinServerTest(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self._base_path = tempfile.mkdtemp()
        self._input_path = os.path.join(self._base_path, 'input')
        self._output_path = os.path.join(self._base_path, 'output')
        os.makedirs(self._input_path)
        os.makedirs(self._output_path)
        _make_fake_data(self._input_path, 10, 10)
        self._reader = ExampleIdReader(self._input_path, FileType.CSV, 'x_1')
        self._writer = ExampleIdWriter(self._output_path, 'x_1')

    def tearDown(self):
        shutil.rmtree(self._base_path)

    def test_start(self):
        joiner = TestJoiner()
        server = DataJoinServer(joiner, self._reader, self._writer)
        server.start(partition_id=2)
        time.sleep(0.1)
        self.assertTrue(os.path.exists(os.path.join(self._output_path, 'partition_2')))

    def test_stop(self):
        joiner = TestJoiner(wait_time=11)
        server = DataJoinServer(joiner, self._reader, self._writer)
        server.start(partition_id=2)
        server.stop()
        time.sleep(2)
        self.assertFalse(os.path.exists(os.path.join(self._output_path, 'partition_2')))
        self.assertFalse(os.path.exists(os.path.join(self._output_path, '0002._SUCCESS')))


if __name__ == '__main__':
    unittest.main()

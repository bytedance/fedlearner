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
import json
import unittest

from pp_lite.data_join.psi_ot.arguments import get_arguments
from pp_lite.proto.arguments_pb2 import Arguments, ClusterSpec


class ArgumentsTest(unittest.TestCase):

    def test_get_client_arguments(self):
        os.environ['INPUT_PATH'] = 'input'
        os.environ['OUTPUT_PATH'] = 'output'
        os.environ['KEY_COLUMN'] = 'raw_id'
        os.environ['INDEX'] = '0'
        os.environ['NUM_WORKERS'] = '1'
        os.environ['JOINER_PORT'] = '12345'
        os.environ['SERVER_PORT'] = '54321'
        os.environ['ROLE'] = 'client'
        args = get_arguments()
        self.assertEqual(
            args,
            Arguments(input_path='input',
                      output_path='output',
                      key_column='raw_id',
                      server_port=54321,
                      joiner_port=12345,
                      worker_rank=0,
                      num_workers=1))
        os.environ['CLUSTER_SPEC'] = json.dumps({'clusterSpec': {'Worker': ['worker-0', 'worker-1']}})
        args = get_arguments()
        cluster_spec = ClusterSpec()
        cluster_spec.workers.extend(['worker-0', 'worker-1'])
        self.assertEqual(
            args,
            Arguments(input_path='input',
                      output_path='output',
                      key_column='raw_id',
                      server_port=54321,
                      joiner_port=12345,
                      worker_rank=0,
                      num_workers=2,
                      cluster_spec=cluster_spec))

    def test_get_light_client_arguments(self):
        os.environ['INPUT_PATH'] = 'input'
        os.environ['OUTPUT_PATH'] = 'output'
        os.environ['KEY_COLUMN'] = 'raw_id'
        os.environ['INDEX'] = '0'
        os.environ['NUM_WORKERS'] = '5'
        os.environ['JOINER_PORT'] = '12345'
        os.environ['SERVER_PORT'] = '54321'
        os.environ['ROLE'] = 'light_client'
        args = get_arguments()
        self.assertEqual(
            args,
            Arguments(input_path='input',
                      output_path='output',
                      key_column='raw_id',
                      server_port=54321,
                      joiner_port=12345,
                      worker_rank=0,
                      num_workers=5))
        os.environ['CLUSTER_SPEC'] = json.dumps({'clusterSpec': {'Worker': ['worker-0', 'worker-1']}})  # omitted
        args = get_arguments()
        self.assertEqual(
            args,
            Arguments(input_path='input',
                      output_path='output',
                      key_column='raw_id',
                      server_port=54321,
                      joiner_port=12345,
                      worker_rank=0,
                      num_workers=5))


if __name__ == '__main__':
    unittest.main()

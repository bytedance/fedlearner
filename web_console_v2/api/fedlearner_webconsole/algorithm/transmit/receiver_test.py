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
import tempfile
import unittest

from google.protobuf.json_format import ParseDict
from envs import Envs
from testing.common import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.algorithm.models import Algorithm, AlgorithmType, Source
from fedlearner_webconsole.algorithm.transmit.receiver import AlgorithmReceiver
from fedlearner_webconsole.algorithm.transmit.sender import AlgorithmSender
from fedlearner_webconsole.algorithm.utils import algorithm_cache_path
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmParameter

_TEST_ALGORITHM_PATH = os.path.join(Envs.BASE_DIR, 'testing/test_data/algorithm/e2e_test')


class AlgorithmReceiverTest(NoWebServerTestCase):

    def test_recv_algorithm_files(self):
        parameter = ParseDict({'variables': [{'name': 'BATCH_SIZE', 'value': '128'}]}, AlgorithmParameter())
        with db.session_scope() as session:
            algo1 = Algorithm(id=1,
                              name='algo-1',
                              uuid='algo-uuid-1',
                              path=_TEST_ALGORITHM_PATH,
                              type=AlgorithmType.NN_VERTICAL,
                              source=Source.USER,
                              comment='comment',
                              version=1)
            algo1.set_parameter(parameter)
            session.commit()
        data_iterator = AlgorithmSender().make_algorithm_iterator(algo1.path)
        receiver = AlgorithmReceiver()
        with tempfile.TemporaryDirectory() as temp_dir:
            resp = next(data_iterator)
            algo_cache_path = algorithm_cache_path(temp_dir, 'algo-uuid-2')
            receiver.write_data_and_extract(data_iterator, algo_cache_path, resp.hash)
            self.assertTrue(os.path.exists(algo_cache_path))
            self.assertEqual(sorted(os.listdir(algo_cache_path)), ['follower', 'leader'])
            with open(os.path.join(algo_cache_path, 'leader', 'main.py'), encoding='utf-8') as f:
                self.assertEqual(f.read(), 'import tensorflow\n')
            with open(os.path.join(algo_cache_path, 'follower', 'main.py'), encoding='utf-8') as f:
                self.assertEqual(f.read(), '')

    def test_write_data_and_extra_when_no_files(self):
        with db.session_scope() as session:
            algo = Algorithm(id=1,
                             name='algo-1',
                             uuid='algo-uuid-1',\
                             type=AlgorithmType.NN_VERTICAL,
                             source=Source.USER,
                             comment='comment',
                             version=1)
            session.commit()
        data_iterator = AlgorithmSender().make_algorithm_iterator(algo.path)
        next(data_iterator)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, 'test')
            AlgorithmReceiver().write_data_and_extract(data_iterator, path)
            self.assertTrue(os.path.exists(path))
            self.assertEqual(os.listdir(path), [])

    def test_write_data_iterator_with_wrong_hash(self):
        with db.session_scope() as session:
            sender = AlgorithmSender()
            data_iterator = sender.make_algorithm_iterator(_TEST_ALGORITHM_PATH)
            # Consumes hash code response first
            next(data_iterator)
            with tempfile.TemporaryDirectory() as temp_dir:
                with self.assertRaises(ValueError):
                    AlgorithmReceiver().write_data_and_extract(data_iterator, temp_dir, 'wrong_hash')


if __name__ == '__main__':
    unittest.main()

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
from envs import Envs
from google.protobuf.json_format import ParseDict
from testing.common import NoWebServerTestCase
from unittest.mock import patch
from fedlearner_webconsole.algorithm.models import Algorithm, Source
from fedlearner_webconsole.algorithm.transmit.sender import AlgorithmSender
from fedlearner_webconsole.algorithm.fetcher import AlgorithmFetcher
from fedlearner_webconsole.algorithm.utils import algorithm_cache_path
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmVariable, AlgorithmParameter
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.proto import remove_secrets

_TEST_ALGORITHM_PATH = os.path.join(Envs.BASE_DIR, 'testing/test_data/algorithm/e2e_test')


class AlgorithmFetcherTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant = Participant(id=1, name='part', domain_name='test')
            project.participants = [participant]
            algo1 = Algorithm(id=1, project_id=1, name='test-algo-1', uuid='algo-1', path=_TEST_ALGORITHM_PATH)
            parameter1 = ParseDict({'variables': [{'name': 'BATCH_SIZE', 'value': '128'}]}, AlgorithmParameter())
            algo1.set_parameter(parameter1)
            algo2 = Algorithm(id=2, project_id=1, name='test-algo-2', uuid='algo-2')
            parameter2 = ParseDict({'variables': [{'name': 'MAX_DEPTH', 'value': '5'}]}, AlgorithmParameter())
            algo2.set_parameter(parameter2)
            session.add_all([participant, project, algo1, algo2])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.get_algorithm')
    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.get_algorithm_files')
    def test_get_algorithm_from_participant(self, mock_get_algorithm_files, mock_get_algorithm):
        with db.session_scope() as session:
            algo = session.query(Algorithm).get(1)
            mock_get_algorithm.return_value = remove_secrets(algo.to_proto())
        mock_get_algorithm_files.return_value = AlgorithmSender().make_algorithm_iterator(algo.path)
        with tempfile.TemporaryDirectory() as temp_dir:
            Envs.STORAGE_ROOT = temp_dir
            algorithm_uuid = 'uuid'
            algorithm = AlgorithmFetcher(project_id=1).get_algorithm_from_participant(algorithm_uuid=algorithm_uuid,
                                                                                      participant_id=1)
            algo_cache_path = algorithm_cache_path(Envs.STORAGE_ROOT, algorithm_uuid)
            self.assertTrue(os.path.exists(algo_cache_path))
            self.assertEqual(algo_cache_path, algorithm.path)
            self.assertEqual(algorithm.source, Source.PARTICIPANT.name)
            self.assertEqual(algorithm.id, 0)
            self.assertEqual(algorithm.algorithm_project_id, 0)
            self.assertEqual(algorithm.parameter,
                             AlgorithmParameter(variables=[AlgorithmVariable(name='BATCH_SIZE', value='128')]))
            self.assertEqual(sorted(os.listdir(algo_cache_path)), ['follower', 'leader'])
            with open(os.path.join(algo_cache_path, 'leader', 'main.py'), encoding='utf-8') as f:
                self.assertEqual(f.read(), 'import tensorflow\n')
            with open(os.path.join(algo_cache_path, 'follower', 'main.py'), encoding='utf-8') as f:
                self.assertEqual(f.read(), '')

    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.get_algorithm')
    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.get_algorithm_files')
    def test_get_algorithm(self, mock_get_algorithm_files, mock_get_algorithm):
        with db.session_scope() as session:
            algo1 = session.query(Algorithm).get(1)
            algo2 = session.query(Algorithm).get(2)
            mock_get_algorithm.return_value = remove_secrets(algo2.to_proto())
        mock_get_algorithm_files.return_value = AlgorithmSender().make_algorithm_iterator(algo1.path)
        with tempfile.TemporaryDirectory() as temp_dir:
            Envs.STORAGE_ROOT = temp_dir
            fetcher = AlgorithmFetcher(project_id=1)
            algorithm1 = fetcher.get_algorithm('algo-1')
            self.assertEqual(algorithm1.path, algo1.path)
            self.assertEqual(algorithm1.parameter,
                             AlgorithmParameter(variables=[AlgorithmVariable(name='BATCH_SIZE', value='128')]))
            algorithm2 = fetcher.get_algorithm('algo-3')
            self.assertEqual(algorithm2.path, algorithm_cache_path(Envs.STORAGE_ROOT, 'algo-3'))
            self.assertEqual(algorithm2.parameter,
                             AlgorithmParameter(variables=[AlgorithmVariable(name='MAX_DEPTH', value='5')]))


if __name__ == '__main__':
    unittest.main()

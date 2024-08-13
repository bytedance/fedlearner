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
import unittest
import tempfile
from envs import Envs
from pathlib import Path
from unittest.mock import patch, MagicMock
from testing.common import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.algorithm.preset_algorithms.preset_algorithm_service import create_algorithm_if_not_exists
from fedlearner_webconsole.algorithm.models import Algorithm, Source, AlgorithmType, AlgorithmProject
from fedlearner_webconsole.utils.file_manager import FileManager

_ALGORITHMS_PATH = Path(__file__, '..').resolve()


class PresetTemplateServiceTest(NoWebServerTestCase):

    def test_create_all(self):
        Envs.STORAGE_ROOT = tempfile.gettempdir()
        create_algorithm_if_not_exists()
        with db.session_scope() as session:
            algorithm = session.query(Algorithm).filter_by(name='e2e_test').first()
            self.assertTrue(os.path.exists(os.path.join(algorithm.path, 'leader', 'main.py')))
            self.assertTrue(os.path.exists(os.path.join(algorithm.path, 'follower', 'main.py')))
            algorithm = session.query(Algorithm).filter_by(name='horizontal_e2e_test').first()
            self.assertEqual(sorted(os.listdir(algorithm.path)), ['follower.py', 'leader.py', 'metrics.py', 'model.py'])
            algorithm = session.query(Algorithm).filter_by(name='secure_boost').first()
            self.assertIsNone(algorithm.path)
            algo_ids = session.query(Algorithm.id).filter_by(source=Source.PRESET).all()
            self.assertEqual(len(algo_ids), 6)

    @patch('fedlearner_webconsole.algorithm.preset_algorithms.preset_algorithm_service.PRESET_ALGORITHM_PROJECT_LIST',
           new_callable=list)
    @patch('fedlearner_webconsole.algorithm.preset_algorithms.preset_algorithm_service.PRESET_ALGORITHM_LIST',
           new_callable=list)
    def test_update_preset_algorithm(self, mock_preset_algorithm_list: MagicMock,
                                     mock_preset_algorithm_project_list: MagicMock):
        mock_preset_algorithm_project_list.extend([
            AlgorithmProject(name='e2e_test',
                             type=AlgorithmType.NN_VERTICAL,
                             uuid='u1b9eea3753e24fd9b91',
                             source=Source.PRESET,
                             comment='algorithm for end to end test',
                             latest_version=4)
        ])
        mock_preset_algorithm_list.extend([
            Algorithm(name='e2e_test',
                      version=1,
                      uuid='u5c4f510aab2f4a288c8',
                      source=Source.PRESET,
                      type=AlgorithmType.NN_VERTICAL,
                      path=os.path.join(_ALGORITHMS_PATH, 'e2e_test_v1'),
                      comment='algorithm for end to end test'),
            Algorithm(name='e2e_test',
                      version=2,
                      uuid='uc74ce6731906480c804',
                      source=Source.PRESET,
                      type=AlgorithmType.NN_VERTICAL,
                      path=os.path.join(_ALGORITHMS_PATH, 'e2e_test_v2'),
                      comment='algorithm for end to end test')
        ])
        file_manager = FileManager()
        Envs.STORAGE_ROOT = tempfile.gettempdir()
        create_algorithm_if_not_exists()
        algo = Algorithm(name='e2e_test',
                         version=3,
                         uuid='e2e_test_version_3',
                         source=Source.PRESET,
                         type=AlgorithmType.NN_VERTICAL,
                         path=os.path.join(_ALGORITHMS_PATH, 'e2e_test_v3'),
                         comment='algorithm for end to end test')
        mock_preset_algorithm_list.append(algo)
        create_algorithm_if_not_exists()
        with db.session_scope() as session:
            algorithm = session.query(Algorithm).filter_by(name='e2e_test', source=Source.PRESET, version=3).first()
            self.assertTrue(os.path.exists(os.path.join(algorithm.path, 'leader', 'main.py')))
            self.assertTrue(os.path.exists(os.path.join(algorithm.path, 'follower', 'main.py')))
            # when algorithm path does not exist
            file_manager.remove(algorithm.path)
            self.assertFalse(file_manager.exists(algorithm.path))
            session.commit()
        create_algorithm_if_not_exists()
        with db.session_scope() as session:
            algorithm = session.query(Algorithm).filter_by(name='e2e_test', source=Source.PRESET, version=3).first()
            self.assertTrue(os.path.exists(os.path.join(algorithm.path, 'leader', 'main.py')))
            self.assertTrue(os.path.exists(os.path.join(algorithm.path, 'follower', 'main.py')))
            # when algorithm path is empty
            file_manager.remove(algorithm.path)
            file_manager.mkdir(algorithm.path)
            self.assertEqual(len(file_manager.ls(algorithm.path)), 0)
        create_algorithm_if_not_exists()
        with db.session_scope() as session:
            algorithm = session.query(Algorithm).filter_by(name='e2e_test', source=Source.PRESET, version=3).first()
            self.assertTrue(os.path.exists(os.path.join(algorithm.path, 'leader', 'main.py')))
            self.assertTrue(os.path.exists(os.path.join(algorithm.path, 'follower', 'main.py')))


if __name__ == '__main__':
    unittest.main()

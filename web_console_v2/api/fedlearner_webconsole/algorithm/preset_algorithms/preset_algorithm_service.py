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
import copy
from envs import Envs
from pathlib import Path
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.utils.file_operator import FileOperator
from fedlearner_webconsole.algorithm.utils import algorithm_path, check_algorithm_file
from fedlearner_webconsole.algorithm.models import Algorithm, Source, AlgorithmType, AlgorithmProject

_ALGORITHMS_PATH = Path(__file__, '..').resolve()

# When inserting a preset algorithm, you need to insert the algorithm project and the algorithm into
# PRESET_ALGORITHM_PROJECT_LIST and PRESET_ALGORITHM_LIST respectively. The algorithm project and the
# algorithm need to have the same name. If the algorithm project already exists, you need to update
# the latest version.

PRESET_ALGORITHM_PROJECT_LIST = [
    AlgorithmProject(name='e2e_test',
                     type=AlgorithmType.NN_VERTICAL,
                     uuid='u1b9eea3753e24fd9b91',
                     source=Source.PRESET,
                     comment='algorithm for end to end test',
                     latest_version=4),
    AlgorithmProject(name='horizontal_e2e_test',
                     type=AlgorithmType.NN_HORIZONTAL,
                     uuid='u76630127d63c4ddb871',
                     source=Source.PRESET,
                     comment='algorithm for end to end test',
                     latest_version=1),
    AlgorithmProject(name='secure_boost',
                     type=AlgorithmType.TREE_VERTICAL,
                     uuid='u7607b76db2c843fb9cd',
                     source=Source.PRESET,
                     comment='algorithm for secure boost',
                     latest_version=1)
]

PRESET_ALGORITHM_LIST = [
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
              comment='algorithm for end to end test'),
    Algorithm(name='e2e_test',
              version=3,
              uuid='u322cd66836f04a13b94',
              source=Source.PRESET,
              type=AlgorithmType.NN_VERTICAL,
              path=os.path.join(_ALGORITHMS_PATH, 'e2e_test_v3'),
              comment='algorithm for end to end test'),
    Algorithm(name='e2e_test',
              version=4,
              uuid='uff7a19e8a1834d5e991',
              source=Source.PRESET,
              type=AlgorithmType.NN_VERTICAL,
              path=os.path.join(_ALGORITHMS_PATH, 'e2e_test_v4'),
              comment='support save result when predict'),
    Algorithm(name='horizontal_e2e_test',
              version=1,
              uuid='ub7b45bf127fc4aebad4',
              source=Source.PRESET,
              type=AlgorithmType.NN_HORIZONTAL,
              path=os.path.join(_ALGORITHMS_PATH, 'horizontal_e2e_test_v1'),
              comment='algorithm for horizontal nn end to end test'),
    Algorithm(name='secure_boost',
              version=1,
              uuid='u936cb7254e4444caaf9',
              source=Source.PRESET,
              type=AlgorithmType.TREE_VERTICAL,
              comment='algorithm for secure boost')
]


def create_algorithm_if_not_exists():
    file_operator = FileOperator()
    file_manager = FileManager()

    for algo_project in PRESET_ALGORITHM_PROJECT_LIST:
        with db.session_scope() as session:
            algorithm_project = session.query(Algorithm).filter_by(name=algo_project.name, source=Source.PRESET).first()
            if algorithm_project is None:
                session.add(algo_project)
                session.commit()

    for preset_algo in PRESET_ALGORITHM_LIST:
        algo = copy.deepcopy(preset_algo)
        dest_algo_path = None
        if preset_algo.path:
            dest_algo_path = algorithm_path(Envs.STORAGE_ROOT, algo.name, algo.version)
            file_manager.mkdir(dest_algo_path)
            with check_algorithm_file(dest_algo_path):
                file_operator.copy_to(preset_algo.path, dest_algo_path)
        algo.path = dest_algo_path
        with db.session_scope() as session:
            algorithm = session.query(Algorithm).filter_by(name=algo.name, version=algo.version,
                                                           source=Source.PRESET).first()
            # Only need to update the path when the algo has been added to the database
            if preset_algo.path and algorithm:
                if algorithm.path and file_manager.exists(algorithm.path):
                    file_manager.remove(algorithm.path)
                algorithm.path = dest_algo_path
            if algorithm is None:
                algo_project = session.query(AlgorithmProject).filter_by(name=algo.name, source=Source.PRESET).first()
                assert algo_project is not None, 'preset algorithm project is not found'
                algo.algorithm_project_id = algo_project.id
                session.add(algo)
            session.commit()

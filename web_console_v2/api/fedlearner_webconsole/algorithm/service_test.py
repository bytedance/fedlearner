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
import tarfile
import tempfile
import unittest

from io import BytesIO
from pathlib import Path
from testing.common import NoWebServerTestCase
from fedlearner_webconsole.algorithm.models import Algorithm, AlgorithmProject, PublishStatus, ReleaseStatus
from fedlearner_webconsole.algorithm.service import AlgorithmService, AlgorithmProjectService
from fedlearner_webconsole.db import db


class AlgorithmServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            algo_project1 = AlgorithmProject(id=1,
                                             name='test-algo-project-1',
                                             publish_status=PublishStatus.PUBLISHED,
                                             release_status=ReleaseStatus.RELEASED)
            algo_project2 = AlgorithmProject(id=2,
                                             name='test-algo-project-2',
                                             latest_version=3,
                                             publish_status=PublishStatus.PUBLISHED,
                                             release_status=ReleaseStatus.RELEASED)
            algo1 = Algorithm(id=1, algorithm_project_id=1, name='test-algo-1', publish_status=PublishStatus.PUBLISHED)
            algo2 = Algorithm(id=2,
                              algorithm_project_id=2,
                              name='test-algo-2',
                              version=1,
                              publish_status=PublishStatus.PUBLISHED)
            algo3 = Algorithm(id=3,
                              algorithm_project_id=2,
                              name='test-algo-3',
                              version=2,
                              publish_status=PublishStatus.PUBLISHED)
            algo4 = Algorithm(id=4,
                              algorithm_project_id=2,
                              name='test-algo-4',
                              version=3,
                              publish_status=PublishStatus.PUBLISHED)
            session.add_all([algo_project1, algo_project2, algo1, algo2, algo3, algo4])
            session.commit()

    def test_delete_algorithm(self):
        with db.session_scope() as session:
            algo1 = session.query(Algorithm).filter_by(name='test-algo-1').first()
            AlgorithmService(session).delete(algo1)
            algo1 = session.query(Algorithm).filter_by(name='test-algo-1').execution_options(
                include_deleted=True).first()
            self.assertIsNone(algo1)
            algo_project1 = session.query(AlgorithmProject).get(1)
            self.assertEqual(algo_project1.release_status, ReleaseStatus.UNRELEASED)

    def test_algorithm_project_status_when_delete_algorithms(self):
        with db.session_scope() as session:
            algo2 = session.query(Algorithm).filter_by(name='test-algo-2').first()
            algo3 = session.query(Algorithm).filter_by(name='test-algo-3').first()
            algo4 = session.query(Algorithm).filter_by(name='test-algo-4').first()
            AlgorithmService(session).delete(algo4)
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project-2').first()
            self.assertEqual(algo_project.publish_status, PublishStatus.PUBLISHED)
            self.assertEqual(algo_project.release_status, ReleaseStatus.UNRELEASED)
            algo_project.release_status = ReleaseStatus.RELEASED
            AlgorithmService(session).delete(algo2)
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project-2').first()
            self.assertEqual(algo_project.publish_status, PublishStatus.PUBLISHED)
            self.assertEqual(algo_project.release_status, ReleaseStatus.RELEASED)
            AlgorithmService(session).delete(algo3)
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project-2').first()
            self.assertEqual(algo_project.publish_status, PublishStatus.UNPUBLISHED)
            self.assertEqual(algo_project.release_status, ReleaseStatus.UNRELEASED)


class AlgorithmProjectServiceTest(NoWebServerTestCase):

    def test_extract_files(self):
        path = tempfile.mkdtemp()
        path = Path(path, 'e2e_test').resolve()
        path.mkdir()
        path.joinpath('follower').mkdir()
        path.joinpath('follower').joinpath('main.py').touch()
        path.joinpath('follower').joinpath('._main.py').touch()
        path.joinpath('follower').joinpath('main.pyc').touch()
        path.joinpath('leader').mkdir()
        path.joinpath('leader').joinpath('___main.py').touch()
        file_path = path.joinpath('leader').joinpath('main.py')
        file_path.touch()
        file_path.write_text('import tensorflow', encoding='utf-8')
        tar_path = os.path.join(tempfile.mkdtemp(), 'test.tar.gz')
        with tarfile.open(tar_path, 'w:gz') as tar:
            tar.add(os.path.join(path, 'leader'), arcname='leader')
            tar.add(os.path.join(path, 'follower'), arcname='follower')
        tar = tarfile.open(tar_path, 'r')  # pylint: disable=consider-using-with
        with tempfile.TemporaryDirectory() as directory:
            with db.session_scope() as session:
                # pylint: disable=protected-access
                AlgorithmProjectService(session)._extract_to(BytesIO(tar.fileobj.read()), directory)
            self.assertTrue(os.path.exists(os.path.join(directory, 'leader', 'main.py')))
            self.assertTrue(os.path.exists(os.path.join(directory, 'follower', 'main.py')))
            self.assertTrue(os.path.exists(os.path.join(directory, 'leader', '___main.py')))
            self.assertFalse(os.path.exists(os.path.join(directory, 'follower', '._main.py')))
            self.assertFalse(os.path.exists(os.path.join(directory, 'follower', 'main.pyc')))
            with open(os.path.join(directory, 'leader', 'main.py'), encoding='utf-8') as fin:
                self.assertEqual(fin.read(), 'import tensorflow')
            with open(os.path.join(directory, 'follower', 'main.py'), encoding='utf-8') as fin:
                self.assertEqual(fin.read(), '')


if __name__ == '__main__':
    unittest.main()

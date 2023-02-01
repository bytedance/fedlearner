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
from unittest.mock import patch, MagicMock
import grpc
from testing.no_web_server_test_case import NoWebServerTestCase
from testing.rpc.client import FakeRpcError
from fedlearner_webconsole.tee.utils import get_project, get_dataset, get_algorithm, get_participant, \
    get_trusted_job_group, get_trusted_job, get_algorithm_with_uuid, get_pure_path
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.algorithm.models import Algorithm
from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.exceptions import InvalidArgumentException, NotFoundException
from fedlearner_webconsole.tee.models import TrustedJobGroup, TrustedJob


class UtilsTest(NoWebServerTestCase):

    def setUp(self) -> None:
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            dataset = Dataset(id=1, name='dataset')
            algorithm = Algorithm(id=1, name='algorithm', project_id=1, uuid='uuid1')
            participant = Participant(id=1, name='part', domain_name='domain')
            group = TrustedJobGroup(id=1, name='trusted-group', project_id=1)
            trusted_job = TrustedJob(id=1, name='V1', version=1, project_id=1, trusted_job_group_id=1)
            session.add_all([project, dataset, algorithm, participant, group, trusted_job])
            session.commit()

    def test_get_project(self):
        with db.session_scope() as session:
            project = get_project(session, 1)
            self.assertEqual(project.name, 'project')
            with self.assertRaises(InvalidArgumentException):
                get_project(session, 2)

    def test_get_dataset(self):
        with db.session_scope() as session:
            dataset = get_dataset(session, 1)
            self.assertEqual(dataset.name, 'dataset')
            with self.assertRaises(InvalidArgumentException):
                get_dataset(session, 2)

    def test_get_algorithm(self):
        with db.session_scope() as session:
            algorithm = get_algorithm(session, 1)
            self.assertEqual(algorithm.name, 'algorithm')
            with self.assertRaises(InvalidArgumentException):
                get_algorithm(session, 2)

    def test_get_participant(self):
        with db.session_scope() as session:
            participant = get_participant(session, 1)
            self.assertEqual(participant.name, 'part')
            with self.assertRaises(InvalidArgumentException):
                get_participant(session, 2)

    def test_get_trusted_job_group(self):
        with db.session_scope() as session:
            group = get_trusted_job_group(session, 1, 1)
            self.assertEqual(group.name, 'trusted-group')
            with self.assertRaises(NotFoundException):
                get_trusted_job_group(session, 1, 2)

    def test_get_trusted_job(self):
        with db.session_scope() as session:
            trusted_job = get_trusted_job(session, 1, 1)
            self.assertEqual(trusted_job.name, 'V1')
            with self.assertRaises(NotFoundException):
                get_trusted_job(session, 1, 2)

    @patch('fedlearner_webconsole.algorithm.fetcher.AlgorithmFetcher.get_algorithm_from_participant')
    def test_get_algorithm_with_uuid(self, mock_get_algorithm: MagicMock):
        mock_get_algorithm.side_effect = FakeRpcError(grpc.StatusCode.NOT_FOUND, 'not found')
        algorithm = get_algorithm_with_uuid(1, 'uuid1')
        self.assertEqual(algorithm.name, 'algorithm')
        with self.assertRaises(InvalidArgumentException):
            get_algorithm_with_uuid(1, 'not-exist')

    def test_get_pure_path(self):
        self.assertEqual(get_pure_path('file:///data/test'), '/data/test')
        self.assertEqual(get_pure_path('/data/test'), '/data/test')
        self.assertEqual(get_pure_path('hdfs:///data/test'), '/data/test')
        self.assertEqual(get_pure_path('hdfs://fl.net/data/test'), '/data/test')


if __name__ == '__main__':
    unittest.main()

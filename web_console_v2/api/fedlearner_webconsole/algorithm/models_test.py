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
from datetime import datetime, timezone
from testing.common import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.algorithm.models import Algorithm, AlgorithmProject, AlgorithmType, Source,\
    PendingAlgorithm, PublishStatus, AlgorithmStatus, normalize_path
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmParameter, AlgorithmVariable, AlgorithmPb,\
    AlgorithmProjectPb
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.pp_datetime import to_timestamp


class AlgorithmTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            algo_project = AlgorithmProject(id=1, name='test-algo-project', uuid='test-algo-project-uuid')
            algo = Algorithm(id=1,
                             algorithm_project_id=1,
                             name='test-algo',
                             type=AlgorithmType.NN_VERTICAL,
                             source=Source.USER,
                             path='/data',
                             created_at=datetime(2022, 2, 22, tzinfo=timezone.utc),
                             updated_at=datetime(2022, 2, 22, tzinfo=timezone.utc))
            algo.set_parameter(AlgorithmParameter(variables=[AlgorithmVariable(name='MAX_ITERS', value='5')]))
            session.add_all([algo_project, algo])
            session.commit()

    def test_parameter(self):
        algo = Algorithm(name='test-algo')
        parameters = AlgorithmParameter(variables=[AlgorithmVariable(name='MAX_ITERS', value='5')])
        algo.set_parameter(parameters)
        self.assertEqual(algo.get_parameter(), parameters)

    def test_to_proto(self):
        parameters = AlgorithmParameter(variables=[
            AlgorithmVariable(
                name='MAX_ITERS', value='5', required=False, display_name='', comment='', value_type='STRING')
        ])
        with db.session_scope() as session:
            algo = session.query(Algorithm).filter_by(name='test-algo').first()
            self.assertEqual(
                algo.to_proto(),
                AlgorithmPb(id=1,
                            name='test-algo',
                            type='NN_VERTICAL',
                            source='USER',
                            algorithm_project_id=1,
                            path='/data',
                            parameter=parameters,
                            status='UNPUBLISHED',
                            algorithm_project_uuid='test-algo-project-uuid',
                            updated_at=to_timestamp(datetime(2022, 2, 22, tzinfo=timezone.utc)),
                            created_at=to_timestamp(datetime(2022, 2, 22, tzinfo=timezone.utc))))

    def test_normalize_path(self):
        path1 = 'hdfs:///user/./local'
        self.assertEqual(normalize_path(path1), 'hdfs:///user/./local')
        path2 = 'file:///app/./local/../tools'
        self.assertEqual(normalize_path(path2), 'file:///app/tools')
        path3 = '/app/./local/../tools'
        self.assertEqual(normalize_path(path3), '/app/tools')

    def test_get_status(self):
        algo1 = Algorithm(publish_status=PublishStatus.PUBLISHED, ticket_uuid=1)
        self.assertEqual(algo1.get_status(), AlgorithmStatus.PUBLISHED)
        algo2 = Algorithm(publish_status=PublishStatus.PUBLISHED, ticket_uuid=None)
        self.assertEqual(algo2.get_status(), AlgorithmStatus.PUBLISHED)
        algo3 = Algorithm(publish_status=PublishStatus.UNPUBLISHED, ticket_uuid=None)
        self.assertEqual(algo3.get_status(), AlgorithmStatus.UNPUBLISHED)
        algo4 = Algorithm(publish_status=PublishStatus.UNPUBLISHED,
                          ticket_uuid=None,
                          ticket_status=TicketStatus.PENDING)
        self.assertEqual(algo4.get_status(), AlgorithmStatus.UNPUBLISHED)
        algo5 = Algorithm(publish_status=PublishStatus.UNPUBLISHED, ticket_uuid=1, ticket_status=TicketStatus.PENDING)
        self.assertEqual(algo5.get_status(), AlgorithmStatus.PENDING_APPROVAL)
        algo6 = Algorithm(publish_status=PublishStatus.UNPUBLISHED, ticket_uuid=1, ticket_status=TicketStatus.DECLINED)
        self.assertEqual(algo6.get_status(), AlgorithmStatus.DECLINED)
        algo7 = Algorithm(publish_status=PublishStatus.UNPUBLISHED, ticket_uuid=1, ticket_status=TicketStatus.APPROVED)
        self.assertEqual(algo7.get_status(), AlgorithmStatus.APPROVED)


class AlgorithmProjectTest(NoWebServerTestCase):

    def test_algorithms_reference(self):
        with db.session_scope() as session:
            algo_project = AlgorithmProject(name='test-algo')
            session.add(algo_project)
            session.flush()
            algo1 = Algorithm(name='test-algo', version=1, algorithm_project_id=algo_project.id)
            algo2 = Algorithm(name='test-algo', version=2, algorithm_project_id=algo_project.id)
            algo3 = Algorithm(name='test-algo')
            session.add_all([algo1, algo2, algo3])
            session.commit()
        with db.session_scope() as session:
            algo_project: AlgorithmProject = session.query(AlgorithmProject).get(algo_project.id)
            algorithms = algo_project.algorithms
            self.assertEqual(len(algorithms), 2)
            self.assertEqual(algorithms[0].name, 'test-algo')
            self.assertEqual(algorithms[0].version, 2)
            self.assertEqual(algorithms[1].name, 'test-algo')
            self.assertEqual(algorithms[1].version, 1)

    def test_to_proto(self):
        with db.session_scope() as session:
            algo_project = AlgorithmProject(id=1,
                                            name='test-algo-project',
                                            type=AlgorithmType.TREE_VERTICAL,
                                            path='/data',
                                            created_at=datetime(2022, 2, 22, tzinfo=timezone.utc),
                                            updated_at=datetime(2022, 2, 22, tzinfo=timezone.utc))
            algo_project.set_parameter(AlgorithmParameter(variables=[AlgorithmVariable(name='MAX_DEPTH', value='5')]))
            session.add(algo_project)
            session.commit()
            result = algo_project.to_proto()
        parameters = AlgorithmParameter(variables=[
            AlgorithmVariable(
                name='MAX_DEPTH', value='5', required=False, display_name='', comment='', value_type='STRING')
        ])
        self.assertEqual(
            result,
            AlgorithmProjectPb(id=1,
                               name='test-algo-project',
                               type='TREE_VERTICAL',
                               source='UNSPECIFIED',
                               publish_status='UNPUBLISHED',
                               path='/data',
                               parameter=parameters,
                               updated_at=to_timestamp(datetime(2022, 2, 22, tzinfo=timezone.utc)),
                               created_at=to_timestamp(datetime(2022, 2, 22, tzinfo=timezone.utc)),
                               release_status='UNRELEASED'))


class PendingAlgorithmTest(NoWebServerTestCase):

    def test_to_dict(self):
        pending_algo = PendingAlgorithm(name='test-algo', type=AlgorithmType.TREE_VERTICAL, path='/data')
        pending_algo.set_parameter(AlgorithmParameter(variables=[AlgorithmVariable(name='MAX_DEPTH', value='5')]))
        with db.session_scope() as session:
            session.add(pending_algo)
            session.commit()
            result = pending_algo.to_proto()
        self.assertEqual(result.type, 'TREE_VERTICAL')
        parameters = AlgorithmParameter(variables=[
            AlgorithmVariable(
                name='MAX_DEPTH', value='5', required=False, display_name='', comment='', value_type='STRING')
        ])
        self.assertEqual(result.parameter, parameters)


if __name__ == '__main__':
    unittest.main()

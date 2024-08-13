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
import tarfile
import unittest
import tempfile
import urllib.parse
import grpc

from envs import Envs
from io import BytesIO
from http import HTTPStatus
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from testing.common import BaseTestCase
from testing.rpc.client import FakeRpcError
from google.protobuf.json_format import ParseDict
from fedlearner_webconsole.db import db
from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.utils.filtering import parse_expression
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.algorithm.transmit.sender import AlgorithmSender
from fedlearner_webconsole.algorithm.models import (Algorithm, AlgorithmType, Source, AlgorithmProject,
                                                    PendingAlgorithm, ReleaseStatus, PublishStatus)
from fedlearner_webconsole.algorithm.utils import algorithm_project_path
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmParameter, AlgorithmVariable, AlgorithmProjectPb, \
    AlgorithmPb
from fedlearner_webconsole.proto.rpc.v2.resource_service_pb2 import ListAlgorithmsResponse,\
    ListAlgorithmProjectsResponse
from fedlearner_webconsole.flag.models import Flag


def generate_algorithm_files():
    path = tempfile.mkdtemp()
    path = Path(path, 'e2e_test').resolve()
    path.mkdir()
    path.joinpath('follower').mkdir()
    path.joinpath('follower').joinpath('main.py').touch()
    path.joinpath('leader').mkdir()
    file_path = path.joinpath('leader').joinpath('main.py')
    file_path.touch()
    file_path.write_text('import tensorflow', encoding='utf-8')
    return str(path)


def _generate_tar_file():
    path = generate_algorithm_files()
    tar_path = os.path.join(tempfile.mkdtemp(), 'test.tar.gz')
    with tarfile.open(tar_path, 'w:gz') as tar:
        tar.add(os.path.join(path, 'leader'), arcname='leader')
        tar.add(os.path.join(path, 'follower'), arcname='follower')
    tar = tarfile.open(tar_path, 'r')  # pylint: disable=consider-using-with
    return tar


class AlgorithmApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            user = User(username='user')
            session.add(user)
            session.flush()
            algo_project1 = AlgorithmProject(id=1, name='test-algo-project-1', uuid='test-algo-project-1-uuid')
            algo1 = Algorithm(name='test-algo-1',
                              version=1,
                              project_id=1,
                              algorithm_project_id=1,
                              path=generate_algorithm_files(),
                              username=user.username,
                              source=Source.PRESET,
                              type=AlgorithmType.NN_VERTICAL)
            algo1.set_parameter(AlgorithmParameter(variables=[AlgorithmVariable(name='BATCH_SIZE', value='123')]))
            algo_project2 = AlgorithmProject(id=2, name='test-algo-project', publish_status=PublishStatus.PUBLISHED)
            algo2 = Algorithm(name='test-algo-2',
                              algorithm_project_id=2,
                              publish_status=PublishStatus.PUBLISHED,
                              path=tempfile.mkdtemp())
            session.add_all([algo_project1, algo_project2, algo1, algo2])
            session.commit()

    def test_get_algorithm_by_id(self):
        with db.session_scope() as session:
            algo = session.query(Algorithm).filter_by(name='test-algo-1').first()
        response = self.get_helper(f'/api/v2/algorithms/{algo.id}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.maxDiff = None
        self.assertResponseDataEqual(response, {
            'name': 'test-algo-1',
            'project_id': 1,
            'status': 'UNPUBLISHED',
            'version': 1,
            'type': 'NN_VERTICAL',
            'source': 'PRESET',
            'username': 'user',
            'algorithm_project_id': 1,
            'algorithm_project_uuid': 'test-algo-project-1-uuid',
            'path': algo.path,
            'parameter': {
                'variables': [{
                    'name': 'BATCH_SIZE',
                    'value': '123',
                    'required': False,
                    'display_name': '',
                    'comment': '',
                    'value_type': 'STRING'
                }]
            },
            'participant_id': 0,
            'participant_name': '',
            'favorite': False,
            'comment': ''
        },
                                     ignore_fields=['id', 'uuid', 'created_at', 'updated_at', 'deleted_at'])

    def test_get_with_not_found_exception(self):
        response = self.get_helper('/api/v2/algorithms/12')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_delete_algorithm(self):
        with db.session_scope() as session:
            algo = session.query(Algorithm).filter_by(name='test-algo-1').first()
        resp = self.delete_helper(f'/api/v2/algorithms/{algo.id}')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        with db.session_scope() as session:
            algo = session.query(Algorithm).filter_by(name='test-algo-1').execution_options(
                include_deleted=True).first()
            self.assertIsNone(algo)

    def test_download_algorithm_files(self):
        with db.session_scope() as session:
            algo = session.query(Algorithm).filter_by(name='test-algo-2').first()
        resp = self.get_helper(f'/api/v2/algorithms/{algo.id}?download=true')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        with db.session_scope() as session:
            algo = session.query(Algorithm).filter_by(name='test-algo-1').first()
        resp = self.get_helper(f'/api/v2/algorithms/{algo.id}?download=true')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(resp.headers['Content-Disposition'], 'attachment; filename=test-algo-1.tar')
        self.assertEqual(resp.headers['Content-Type'], 'application/x-tar')
        tar = tarfile.TarFile(fileobj=BytesIO(resp.data))  # pylint: disable=consider-using-with
        with tempfile.TemporaryDirectory() as temp_dir:
            tar.extractall(temp_dir)
            self.assertEqual(['follower', 'leader'], sorted(os.listdir(temp_dir)))
            self.assertEqual(['main.py'], os.listdir(os.path.join(temp_dir, 'follower')))
            self.assertEqual(['main.py'], os.listdir(os.path.join(temp_dir, 'leader')))

    def test_patch_algorithm(self):
        with db.session_scope() as session:
            algo = session.query(Algorithm).filter_by(name='test-algo-1').first()
        resp = self.patch_helper(f'/api/v2/algorithms/{algo.id}', data={'comment': 'test edit comment'})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            algorithm = session.query(Algorithm).filter_by(id=algo.id).first()
            self.assertEqual(algorithm.comment, 'test edit comment')


class AlgorithmsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='test-project')
            algo_project = AlgorithmProject(id=1, name='test-algo-project')
            algo1 = Algorithm(name='test-algo-1', algorithm_project_id=1, project_id=1)
            algo2 = Algorithm(name='test-algo-2', algorithm_project_id=1, project_id=1)
            algo3 = Algorithm(name='test-algo-3', algorithm_project_id=2, project_id=1)
            session.add_all([project, algo_project, algo1, algo2, algo3])
            session.commit()

    def test_get_algorithms_by_algo_project_id(self):
        resp = self.get_helper('/api/v2/projects/1/algorithms?algo_project_id=1')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'test-algo-2')
        self.assertEqual(data[1]['name'], 'test-algo-1')
        resp = self.get_helper('/api/v2/projects/0/algorithms?algo_project_id=1')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 2)
        resp = self.get_helper('/api/v2/projects/0/algorithms')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 3)


class AlgorithmFilesApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        path = generate_algorithm_files()
        with db.session_scope() as session:
            algo = Algorithm(name='test-algo', path=path)
            session.add(algo)
            session.commit()

    def test_get_algorithm_tree(self):
        with db.session_scope() as session:
            algo = session.query(Algorithm).filter_by(name='test-algo').first()
        resp = self.get_helper(f'/api/v2/algorithms/{algo.id}/tree')
        data = self.get_response_data(resp)
        data = sorted(data, key=lambda d: d['filename'])
        self.assertPartiallyEqual(data[1], {
            'filename': 'leader',
            'path': 'leader',
            'is_directory': True
        },
                                  ignore_fields=['size', 'mtime', 'files'])
        self.assertPartiallyEqual(data[1]['files'][0], {
            'filename': 'main.py',
            'path': 'leader/main.py',
            'is_directory': False
        },
                                  ignore_fields=['size', 'mtime', 'files'])

    def test_get_algorithm_files(self):
        with db.session_scope() as session:
            algo = session.query(Algorithm).filter_by(name='test-algo').first()
        resp = self.get_helper(f'/api/v2/algorithms/{algo.id}/files?path=..')
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        resp = self.get_helper(f'/api/v2/algorithms/{algo.id}/files?path=leader')
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        resp = self.get_helper(f'/api/v2/algorithms/{algo.id}/files?path=leader/config.py')
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        resp = self.get_helper(f'/api/v2/algorithms/{algo.id}/files?path=leader/main.py')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {'content': 'import tensorflow', 'path': 'leader/main.py'})


class AlgorithmFilesDownloadApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        path = generate_algorithm_files()
        with db.session_scope() as session:
            algo = Algorithm(name='test-algo', project_id=1, path=path)
            session.add(algo)
            session.commit()


class AlgorithmProjectsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(name='test-project')
            session.add(project)
            session.commit()

    def test_get_algorithms(self):
        with db.session_scope() as session:
            algo_project_1 = AlgorithmProject(name='test-algo-1', created_at=datetime(2021, 12, 1, 0, 0, 0))
            algo_project_2 = AlgorithmProject(name='test-algo-2',
                                              project_id=1,
                                              created_at=datetime(2021, 12, 1, 0, 0, 1))
            session.add_all([algo_project_1, algo_project_2])
            session.commit()
        # test get all
        response = self.get_helper('/api/v2/projects/0/algorithm_projects')
        data = self.get_response_data(response)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'test-algo-2')
        # test get by project
        response = self.get_helper('/api/v2/projects/1/algorithm_projects')
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'test-algo-2')
        # test get by keyword
        response = self.get_helper('/api/v2/projects/0/algorithm_projects?keyword=algo-2')
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'test-algo-2')

    def test_get_algorithms_by_source(self):
        with db.session_scope() as session:
            algo_project_1 = AlgorithmProject(name='test-preset-1', source=Source.PRESET)
            algo_project_2 = AlgorithmProject(name='test-preset-2',
                                              source=Source.USER,
                                              created_at=datetime(2021, 12, 1, 0, 0, 0))
            algo_project_3 = AlgorithmProject(name='test-preset-3',
                                              source=Source.THIRD_PARTY,
                                              created_at=datetime(2021, 12, 1, 0, 0, 1))
            session.add_all([algo_project_1, algo_project_2, algo_project_3])
            session.commit()
        response = self.get_helper('/api/v2/projects/0/algorithm_projects?sources=PRESET')
        data = self.get_response_data(response)
        self.assertEqual(data[0]['name'], 'test-preset-1')
        response = self.get_helper('/api/v2/projects/0/algorithm_projects?sources=USER&sources=THIRD_PARTY')
        data = self.get_response_data(response)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'test-preset-3')
        self.assertEqual(data[1]['name'], 'test-preset-2')

    def test_get_algorithm_projects_by_filter(self):
        with db.session_scope() as session:
            algo_project_1 = AlgorithmProject(name='test-algo-1',
                                              release_status=ReleaseStatus.RELEASED,
                                              type=AlgorithmType.NN_VERTICAL,
                                              created_at=datetime(2021, 12, 1, 0, 0, 0),
                                              updated_at=datetime(2021, 12, 5, 3, 0, 0))
            algo_project_2 = AlgorithmProject(name='test-algo-2',
                                              release_status=ReleaseStatus.UNRELEASED,
                                              type=AlgorithmType.TREE_VERTICAL,
                                              created_at=datetime(2021, 12, 2, 0, 0, 0),
                                              updated_at=datetime(2021, 12, 5, 4, 0, 0))
            algo_project_3 = AlgorithmProject(name='test-preset-1',
                                              release_status=ReleaseStatus.RELEASED,
                                              type=AlgorithmType.NN_VERTICAL,
                                              created_at=datetime(2021, 12, 3, 0, 0, 0),
                                              updated_at=datetime(2021, 12, 5, 2, 0, 0))
            algo_project_4 = AlgorithmProject(name='test-preset-2',
                                              release_status=ReleaseStatus.UNRELEASED,
                                              type=AlgorithmType.TREE_VERTICAL,
                                              created_at=datetime(2021, 12, 4, 0, 0, 0),
                                              updated_at=datetime(2021, 12, 5, 1, 0, 0))
            session.add_all([algo_project_1, algo_project_2, algo_project_3, algo_project_4])
            session.commit()
        resp = self.get_helper('/api/v2/projects/0/algorithm_projects')
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 4)
        filter_param = urllib.parse.quote('(type:["NN_VERTICAL"])')
        resp = self.get_helper(f'/api/v2/projects/0/algorithm_projects?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['test-preset-1', 'test-algo-1'])
        filter_param = urllib.parse.quote('(release_status:["UNRELEASED"])')
        resp = self.get_helper(f'/api/v2/projects/0/algorithm_projects?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['test-preset-2', 'test-algo-2'])
        filter_param = urllib.parse.quote('(name~="test-algo")')
        resp = self.get_helper(f'/api/v2/projects/0/algorithm_projects?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['test-algo-2', 'test-algo-1'])
        order_by_param = urllib.parse.quote('created_at asc')
        resp = self.get_helper(f'/api/v2/projects/0/algorithm_projects?order_by={order_by_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['test-algo-1', 'test-algo-2', 'test-preset-1', 'test-preset-2'])
        order_by_param = urllib.parse.quote('updated_at asc')
        resp = self.get_helper(f'/api/v2/projects/0/algorithm_projects?order_by={order_by_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['test-preset-2', 'test-preset-1', 'test-algo-1', 'test-algo-2'])

    def test_post_algorithm_project_with_wrong_parameter(self):
        with db.session_scope() as session:
            project = session.query(Project).filter_by(name='test-project').first()
        parameters = {'variable': []}
        resp = self.post_helper(f'/api/v2/projects/{project.id}/algorithm_projects',
                                data={
                                    'name': 'test-algo-project',
                                    'type': AlgorithmType.NN_VERTICAL.name,
                                    'parameter': json.dumps(parameters)
                                })
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

    @patch('fedlearner_webconsole.algorithm.service.AlgorithmProject')
    @patch('fedlearner_webconsole.algorithm.apis.algorithm_project_path')
    def test_post_algorithm_project_with_exceptions(self, mock_algorithm_project_path, mock_algorithm_project):
        with db.session_scope() as session:
            project = session.query(Project).filter_by(name='test-project').first()
        parameters = {'variables': [{'name': 'BATCH_SIZE', 'value': '128'}]}
        file = (BytesIO(_generate_tar_file().fileobj.read()), 'test.tar.gz')
        Envs.STORAGE_ROOT = tempfile.mkdtemp()
        name = 'test-algo-project'
        path = os.path.join(Envs.STORAGE_ROOT, 'algorithm_projects', name)
        mock_algorithm_project_path.return_value = path
        mock_algorithm_project.side_effect = Exception()
        self.client.post(f'/api/v2/projects/{project.id}/algorithm_projects',
                         data={
                             'name': name,
                             'file': [file],
                             'type': AlgorithmType.NN_VERTICAL.name,
                             'parameter': json.dumps(parameters),
                             'comment': 'haha'
                         },
                         content_type='multipart/form-data',
                         headers=self._get_headers())
        self.assertFalse(os.path.exists(path))

    def test_post_algorithm_project(self):
        with db.session_scope() as session:
            project = session.query(Project).filter_by(name='test-project').first()
        parameters = {'variables': [{'name': 'BATCH_SIZE', 'value': '128'}]}
        file = (BytesIO(_generate_tar_file().fileobj.read()), 'test.tar.gz')
        Envs.STORAGE_ROOT = tempfile.mkdtemp()
        resp = self.client.post(f'/api/v2/projects/{project.id}/algorithm_projects',
                                data={
                                    'name': 'test-algo-project',
                                    'file': [file],
                                    'type': AlgorithmType.NN_VERTICAL.name,
                                    'parameter': json.dumps(parameters),
                                    'comment': 'haha'
                                },
                                content_type='multipart/form-data',
                                headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            algo_project: AlgorithmProject = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
            self.assertEqual(algo_project.type, AlgorithmType.NN_VERTICAL)
            algo_parameter = ParseDict(parameters, AlgorithmParameter())
            self.assertEqual(algo_project.get_parameter(), algo_parameter)
            self.assertEqual(algo_project.comment, 'haha')
        self.assertTrue(os.path.exists(os.path.join(algo_project.path, 'leader', 'main.py')))
        self.assertTrue(os.path.exists(os.path.join(algo_project.path, 'follower', 'main.py')))
        with open(os.path.join(algo_project.path, 'leader', 'main.py'), encoding='utf-8') as fin:
            self.assertEqual(fin.read(), 'import tensorflow')
        with open(os.path.join(algo_project.path, 'follower', 'main.py'), encoding='utf-8') as fin:
            self.assertEqual(fin.read(), '')

    def test_post_algorithm_project_with_empty_file(self):
        with db.session_scope() as session:
            project = session.query(Project).filter_by(name='test-project').first()
        Envs.STORAGE_ROOT = tempfile.mkdtemp()
        resp = self.client.post(f'/api/v2/projects/{project.id}/algorithm_projects',
                                data={
                                    'name': 'test-algo-project',
                                    'type': AlgorithmType.NN_VERTICAL.name,
                                },
                                content_type='multipart/form-data',
                                headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
            self.assertEqual(algo_project.name, 'test-algo-project')
            self.assertEqual(algo_project.type, AlgorithmType.NN_VERTICAL)
            self.assertEqual(algo_project.get_parameter(), AlgorithmParameter())
        self.assertTrue(os.path.exists(algo_project.path))
        self.assertEqual(os.listdir(algo_project.path), [])

    @patch('fedlearner_webconsole.utils.file_manager.FileManager.mkdir')
    def test_post_algorithm_project_with_duplicate_name(self, mock_mkdir):
        with db.session_scope() as session:
            project1 = Project(id=2, name='test-project-1')
            project2 = Project(id=3, name='test-project-2')
            algo_project = AlgorithmProject(name='test-algo-project', project_id=2, source=Source.USER)
            session.add_all([project1, project2, algo_project])
            session.commit()
        resp = self.client.post('/api/v2/projects/2/algorithm_projects',
                                data={
                                    'name': 'test-algo-project',
                                    'type': AlgorithmType.NN_VERTICAL.name,
                                },
                                content_type='multipart/form-data',
                                headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.CONFLICT)
        resp = self.client.post('/api/v2/projects/3/algorithm_projects',
                                data={
                                    'name': 'test-algo-project',
                                    'type': AlgorithmType.TREE_VERTICAL.name,
                                },
                                content_type='multipart/form-data',
                                headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)

    def test_post_algorithm_project_with_trusted_computing(self):
        Flag.TRUSTED_COMPUTING_ENABLED.value = True
        with db.session_scope() as session:
            project = session.query(Project).filter_by(name='test-project').first()
        parameters = {'variables': [{'name': 'OUTPUT_PATH', 'value': '/output'}]}
        file = (BytesIO(_generate_tar_file().fileobj.read()), 'test.tar.gz')
        Envs.STORAGE_ROOT = tempfile.mkdtemp()
        golden_data = {
            'name': 'test-algo-project-trust',
            'file': [file],
            'type': AlgorithmType.TRUSTED_COMPUTING.name,
            'parameter': json.dumps(parameters),
            'comment': 'comment for algorithm project with trusted computing type'
        }
        resp = self.client.post(f'/api/v2/projects/{project.id}/algorithm_projects',
                                data=golden_data,
                                content_type='multipart/form-data',
                                headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            algo_project: AlgorithmProject = \
                session.query(AlgorithmProject).filter_by(name=golden_data['name']).first()
            self.assertEqual(algo_project.type.name, golden_data['type'])
            algo_parameter = ParseDict(parameters, AlgorithmParameter())
            self.assertEqual(algo_project.get_parameter(), algo_parameter)
            self.assertEqual(algo_project.comment, golden_data['comment'])
        self.assertTrue(os.path.exists(os.path.join(algo_project.path, 'leader', 'main.py')))
        self.assertTrue(os.path.exists(os.path.join(algo_project.path, 'follower', 'main.py')))
        with open(os.path.join(algo_project.path, 'leader', 'main.py'), encoding='utf-8') as fin:
            self.assertEqual(fin.read(), 'import tensorflow')
        with open(os.path.join(algo_project.path, 'follower', 'main.py'), encoding='utf-8') as fin:
            self.assertEqual(fin.read(), '')


class AlgorithmProjectApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            user = User(username='test-user')
            session.add(user)
            session.flush()
            algo_project = AlgorithmProject(name='test-algo-project',
                                            type=AlgorithmType.NN_VERTICAL,
                                            project_id=1,
                                            username=user.username,
                                            source=Source.PRESET,
                                            path=generate_algorithm_files(),
                                            comment='comment')
            parameter = {
                'variables': [{
                    'name': 'BATCH_SIZE',
                    'value': '12',
                    'display_name': 'batch_size',
                    'required': False,
                    'comment': '',
                    'value_type': 'STRING'
                }]
            }
            algo_parameter = ParseDict(parameter, AlgorithmParameter())
            algo_project.set_parameter(algo_parameter)
            session.add(algo_project)
            algo_project = AlgorithmProject(name='test-algo-project-third-party',
                                            type=AlgorithmType.NN_VERTICAL,
                                            project_id=1,
                                            username=user.username,
                                            source=Source.THIRD_PARTY,
                                            path=generate_algorithm_files(),
                                            comment='comment')
            session.add(algo_project)
            session.commit()

    def test_get_algorithm_project(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
            parameter = to_dict(algo_project.get_parameter())
        resp = self.get_helper(f'/api/v2/algorithm_projects/{algo_project.id}')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        expected_data = {
            'algorithms': [],
            'name': 'test-algo-project',
            'type': 'NN_VERTICAL',
            'project_id': 1,
            'username': 'test-user',
            'latest_version': 0,
            'source': 'PRESET',
            'participant_id': 0,
            'participant_name': '',
            'parameter': parameter,
            'publish_status': 'UNPUBLISHED',
            'release_status': 'UNRELEASED',
            'path': algo_project.path,
            'comment': 'comment'
        }
        self.maxDiff = None
        self.assertResponseDataEqual(resp,
                                     expected_data,
                                     ignore_fields=['id', 'uuid', 'created_at', 'updated_at', 'deleted_at'])

    def test_get_algorithms_from_algorithm_project(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
            algo_1 = Algorithm(name='test-algo', version=1, algorithm_project_id=algo_project.id)
            algo_2 = Algorithm(name='test-algo', version=2, algorithm_project_id=algo_project.id)
            session.add_all([algo_1, algo_2])
            session.commit()
        resp = self.get_helper(f'/api/v2/algorithm_projects/{algo_project.id}')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(len(data['algorithms']), 2)

    def test_patch_algorithm_project(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
        parameters = {'variables': [{'name': 'BATCH_SIZE', 'value': '128'}]}
        resp = self.patch_helper(f'/api/v2/algorithm_projects/{algo_project.id}',
                                 data={
                                     'parameter': parameters,
                                     'comment': 'comment'
                                 })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).get(algo_project.id)
            self.assertEqual(algo_project.comment, 'comment')
            algo_parameter = ParseDict(parameters, AlgorithmParameter())
            self.assertEqual(algo_project.get_parameter(), algo_parameter)

    def test_patch_third_party_algorithm_project(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project-third-party').first()
        comment = 'test edit comment'
        resp = self.patch_helper(f'/api/v2/algorithm_projects/{algo_project.id}',
                                 data={
                                     'parameter': None,
                                     'comment': comment
                                 })
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).get(algo_project.id)
            self.assertNotEqual(algo_project.comment, comment)

    def test_delete_algorithm_project(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
            algo = Algorithm(name='test-algo', algorithm_project_id=algo_project.id, path=generate_algorithm_files())
            session.add(algo)
            session.commit()
        resp = self.delete_helper(f'/api/v2/algorithm_projects/{algo.id}')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter(
                AlgorithmProject.name.like('%test-algo-project')).execution_options(include_deleted=True).first()
            algo = session.query(Algorithm).filter(
                Algorithm.name.like('%test-algo')).execution_options(include_deleted=True).first()
            self.assertIsNone(algo_project)
            self.assertIsNone(algo)


class AlgorithmProjectFilesApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        path = generate_algorithm_files()
        with db.session_scope() as session:
            algo_project = AlgorithmProject(name='test-algo-project', path=path)
            session.add(algo_project)
            session.commit()

    def test_get_file_tree(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
        resp = self.get_helper(f'/api/v2/algorithm_projects/{algo_project.id}/tree')
        data = self.get_response_data(resp)
        data = sorted(data, key=lambda d: d['filename'])
        self.assertPartiallyEqual(data[1], {
            'filename': 'leader',
            'path': 'leader',
            'is_directory': True
        },
                                  ignore_fields=['size', 'mtime', 'files'])
        self.assertPartiallyEqual(data[1]['files'][0], {
            'filename': 'main.py',
            'path': 'leader/main.py',
            'is_directory': False
        },
                                  ignore_fields=['size', 'mtime', 'files'])

    def test_get_project_files(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
        resp = self.get_helper(f'/api/v2/algorithm_projects/{algo_project.id}/files?path=leader/../..')
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        resp = self.get_helper(f'/api/v2/algorithm_projects/{algo_project.id}/files?path=leader/config.py')
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        resp = self.get_helper(f'/api/v2/algorithm_projects/{algo_project.id}/files?path=leader')
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        resp = self.get_helper(f'/api/v2/algorithm_projects/{algo_project.id}/files?path=leader/main.py')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {'content': 'import tensorflow', 'path': 'leader/main.py'})

    def test_post_project_files(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
        # unauthorized path under algorithm
        data = {'path': '..', 'filename': 'test', 'file': (BytesIO(b'abcdef'), 'test.jpg')}
        resp = self.client.post(f'/api/v2/algorithm_projects/{algo_project.id}/files',
                                data=data,
                                content_type='multipart/form-data',
                                headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        # fail due to path not found
        data = {'path': 'test', 'filename': ',.test.jpg.', 'file': (BytesIO(b'abcdef'), 'test.jpg')}
        resp = self.client.post(f'/api/v2/algorithm_projects/{algo_project.id}/files',
                                data=data,
                                content_type='multipart/form-data',
                                headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        # put file under leader directory
        data = {'path': 'leader', 'filename': ',.test.jpg.', 'file': (BytesIO(b'abcdef'), 'test.jpg')}
        resp = self.client.post(f'/api/v2/algorithm_projects/{algo_project.id}/files',
                                data=data,
                                content_type='multipart/form-data',
                                headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {'path': 'leader', 'filename': 'test.jpg'})
        with open(os.path.join(algo_project.path, 'leader', 'test.jpg'), 'rb') as fin:
            file_content = fin.read()
            self.assertEqual(file_content, b'abcdef')
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
            self.assertEqual(algo_project.release_status, ReleaseStatus.UNRELEASED)

    def test_put_empty_file(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
        # put empty file under leader directory
        data = {'path': 'leader', 'filename': 'test'}
        resp = self.client.put(f'/api/v2/algorithm_projects/{algo_project.id}/files',
                               data=data,
                               content_type='multipart/form-data',
                               headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {'content': None, 'path': 'leader', 'filename': 'test'})
        self.assertTrue(os.path.exists(os.path.join(algo_project.path, 'leader', 'test')))

    def test_put_file_by_content(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
        # put file under leader directory by content
        data = {'path': 'leader', 'filename': 'test', 'file': BytesIO(b'123')}
        resp = self.client.put(f'/api/v2/algorithm_projects/{algo_project.id}/files',
                               data=data,
                               content_type='multipart/form-data',
                               headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {'path': 'leader', 'filename': 'test', 'content': '123'})
        with open(os.path.join(algo_project.path, 'leader', 'test'), 'r', encoding='utf-8') as file:
            self.assertEqual(file.read(), '123')

    def test_put_directory(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
        # fail due to file already exist
        data = {'path': '.', 'filename': 'leader', 'is_directory': True}
        resp = self.client.put(f'/api/v2/algorithm_projects/{algo_project.id}/files',
                               data=data,
                               content_type='multipart/form-data',
                               headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        # fail due to path not exist
        data = {'path': 'test', 'filename': 'test', 'is_directory': True}
        resp = self.client.put(f'/api/v2/algorithm_projects/{algo_project.id}/files',
                               data=data,
                               content_type='multipart/form-data',
                               headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        # create directory under leader
        data = {'path': 'leader', 'filename': 'test', 'is_directory': True}
        resp = self.client.put(f'/api/v2/algorithm_projects/{algo_project.id}/files',
                               data=data,
                               content_type='multipart/form-data',
                               headers=self._get_headers())
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {'content': None, 'path': 'leader', 'filename': 'test'})
        self.assertTrue(os.path.isdir(os.path.join(algo_project.path, 'leader', 'test')))
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
            self.assertEqual(algo_project.release_status, ReleaseStatus.UNRELEASED)

    def test_delete_project_files(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
        resp = self.delete_helper(f'/api/v2/algorithm_projects/{algo_project.id}/files?path=leader/../..')
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        resp = self.delete_helper(f'/api/v2/algorithm_projects/{algo_project.id}/files?path=leader/config.py')
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        resp = self.delete_helper(f'/api/v2/algorithm_projects/{algo_project.id}/files?path=leader/main.py')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        self.assertTrue(os.path.exists(os.path.join(algo_project.path, 'leader')))
        self.assertFalse(os.path.exists(os.path.join(algo_project.path, 'leader', 'main.py')))
        resp = self.delete_helper(f'/api/v2/algorithm_projects/{algo_project.id}/files?path=follower')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(os.listdir(os.path.join(algo_project.path)), ['leader'])
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
            self.assertEqual(algo_project.release_status, ReleaseStatus.UNRELEASED)

    def test_patch_algorithm_project_file_rename(self):
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
        resp = self.patch_helper(f'/api/v2/algorithm_projects/{algo_project.id}/files',
                                 data={
                                     'path': 'leader',
                                     'dest': 'leader1'
                                 })
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        self.assertTrue(os.path.exists(os.path.join(algo_project.path, 'leader1')))
        self.assertFalse(os.path.exists(os.path.join(algo_project.path, 'leader')))
        resp = self.patch_helper(f'/api/v2/algorithm_projects/{algo_project.id}/files',
                                 data={
                                     'path': 'leader1/main.py',
                                     'dest': 'main.py'
                                 })
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        self.assertTrue(os.path.exists(os.path.join(algo_project.path, 'main.py')))
        self.assertFalse(os.path.exists(os.path.join(algo_project.path, 'leader', 'main.py')))
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
            self.assertEqual(algo_project.release_status, ReleaseStatus.UNRELEASED)


class ParticipantAlgorithmProjectsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project-1')
            participant_1 = Participant(id=1, name='part-1', domain_name='test-1')
            participant_2 = Participant(id=2, name='part-2', domain_name='test-2')
            project_participant_1 = ProjectParticipant(id=1, project_id=1, participant_id=1)
            project_participant_2 = ProjectParticipant(id=2, project_id=1, participant_id=2)
            algorithm_project_1 = AlgorithmProject(id=1,
                                                   uuid='algo-project-uuid-1',
                                                   name='test-algo-project-1',
                                                   type=AlgorithmType.NN_VERTICAL,
                                                   source=Source.PRESET,
                                                   latest_version=1,
                                                   comment='comment-1',
                                                   created_at=datetime(2021, 12, 3, 0, 0, 0),
                                                   updated_at=datetime(2021, 12, 7, 2, 0, 0))
            algorithm_project_2 = AlgorithmProject(id=2,
                                                   uuid='algo-project-uuid-2',
                                                   name='test-algo-project-2',
                                                   type=AlgorithmType.NN_VERTICAL,
                                                   source=Source.USER,
                                                   latest_version=1,
                                                   comment='comment-2',
                                                   created_at=datetime(2021, 12, 4, 0, 0, 0),
                                                   updated_at=datetime(2021, 12, 6, 2, 0, 0))
            session.add_all([
                project, participant_1, participant_2, project_participant_1, project_participant_2,
                algorithm_project_1, algorithm_project_2
            ])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.list_algorithm_projects')
    def test_get_participant_algorithm_projects(self, mock_list_algorithm_projects):
        with db.session_scope() as session:
            algo_project_1 = session.query(AlgorithmProject).get(1)
            algo_project_2 = session.query(AlgorithmProject).get(2)
            participant_algorithm_projects1 = [algo_project_1.to_proto()]
            participant_algorithm_projects2 = [algo_project_2.to_proto()]
        mock_list_algorithm_projects.return_value = ListAlgorithmProjectsResponse(
            algorithm_projects=participant_algorithm_projects1)
        resp = self.get_helper('/api/v2/projects/1/participants/1/algorithm_projects')
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 1)
        self.assertEqual(mock_list_algorithm_projects.call_count, 1)
        self.assertEqual(data[0]['uuid'], 'algo-project-uuid-1')
        self.assertEqual(data[0]['latest_version'], 1)
        self.assertEqual(data[0]['comment'], 'comment-1')
        self.assertEqual(data[0]['participant_id'], 1)
        mock_list_algorithm_projects.side_effect = [
            ListAlgorithmProjectsResponse(algorithm_projects=participant_algorithm_projects1),
            ListAlgorithmProjectsResponse(algorithm_projects=participant_algorithm_projects2)
        ]
        resp = self.get_helper('/api/v2/projects/1/participants/0/algorithm_projects')
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 2)
        self.assertEqual(mock_list_algorithm_projects.call_count, 3)
        self.assertEqual(data[0]['uuid'], 'algo-project-uuid-2')
        self.assertEqual(data[0]['latest_version'], 1)
        self.assertEqual(data[0]['comment'], 'comment-2')
        self.assertEqual(data[0]['participant_id'], 2)
        self.assertEqual(data[1]['name'], 'test-algo-project-1')
        self.assertEqual(data[1]['source'], 'PRESET')
        self.assertEqual(data[1]['participant_id'], 1)
        # when grpc error
        mock_list_algorithm_projects.side_effect = [
            FakeRpcError(grpc.StatusCode.UNIMPLEMENTED, 'rpc not implemented'),
            ListAlgorithmProjectsResponse(algorithm_projects=participant_algorithm_projects2)
        ]
        resp = self.get_helper('/api/v2/projects/1/participants/0/algorithm_projects')
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 1)
        mock_list_algorithm_projects.side_effect = [
            FakeRpcError(grpc.StatusCode.UNIMPLEMENTED, 'rpc not implemented'),
            FakeRpcError(grpc.StatusCode.UNIMPLEMENTED, 'rpc not implemented')
        ]
        resp = self.get_helper('/api/v2/projects/1/participants/0/algorithm_projects')
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 0)

    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.list_algorithm_projects')
    def test_get_participant_algorithm_projects_with_filter(self, mock_list_algorithm_projects):
        with db.session_scope() as session:
            algo_project_1 = session.query(AlgorithmProject).get(1)
            algo_project_2 = session.query(AlgorithmProject).get(2)
            participant_algorithm_projects1 = [algo_project_1.to_proto()]
            participant_algorithm_projects2 = [algo_project_1.to_proto(), algo_project_2.to_proto()]
        mock_list_algorithm_projects.return_value = ListAlgorithmProjectsResponse(
            algorithm_projects=participant_algorithm_projects1)
        filter_param = urllib.parse.quote('(name~="1")')
        resp = self.get_helper(f'/api/v2/projects/1/participants/1/algorithm_projects?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['uuid'], 'algo-project-uuid-1')
        self.assertEqual(data[0]['latest_version'], 1)
        self.assertEqual(data[0]['comment'], 'comment-1')
        mock_list_algorithm_projects.assert_called_with(filter_exp=parse_expression('(name~="1")'))
        mock_list_algorithm_projects.return_value = ListAlgorithmProjectsResponse(
            algorithm_projects=participant_algorithm_projects2)
        order_by_param = urllib.parse.quote('updated_at asc')
        resp = self.get_helper(f'/api/v2/projects/1/participants/1/algorithm_projects?order_by={order_by_param}')
        data = self.get_response_data(resp)
        self.assertEqual(data[0]['name'], 'test-algo-project-2')
        self.assertEqual(data[1]['uuid'], 'algo-project-uuid-1')
        mock_list_algorithm_projects.return_value = ListAlgorithmProjectsResponse(
            algorithm_projects=participant_algorithm_projects2)
        order_by_param = urllib.parse.quote('created_at asc')
        resp = self.get_helper(f'/api/v2/projects/1/participants/1/algorithm_projects?order_by={order_by_param}')
        data = self.get_response_data(resp)
        self.assertEqual(data[0]['name'], 'test-algo-project-1')
        self.assertEqual(data[1]['uuid'], 'algo-project-uuid-2')
        order_by_param = urllib.parse.quote('unknown_attribute asc')
        resp = self.get_helper(f'/api/v2/projects/1/participants/1/algorithm_projects?order_by={order_by_param}')
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)


class ParticipantAlgorithmProjectApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project-1')
            participant = Participant(id=1, name='part-1', domain_name='test')
            session.add_all([project, participant])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.get_algorithm_project')
    def test_get_algorithm_project(self, mock_get_algorithm_project):
        participant_algorithm_project = AlgorithmProjectPb(uuid='algo-project-uuid-1',
                                                           name='test-algo-project-1',
                                                           type=AlgorithmType.NN_VERTICAL.name,
                                                           source=Source.USER.name,
                                                           latest_version=1,
                                                           comment='comment-1',
                                                           created_at=1326542405,
                                                           updated_at=1326542405)
        mock_get_algorithm_project.return_value = participant_algorithm_project
        resp = self.get_helper('/api/v2/projects/1/participants/1/algorithm_projects/algo-project-uuid-1')
        data = self.get_response_data(resp)
        self.assertEqual(data['uuid'], 'algo-project-uuid-1')
        self.assertEqual(data['latest_version'], 1)
        self.assertEqual(data['comment'], 'comment-1')


class ParticipantAlgorithmsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project-1')
            participant = Participant(id=1, name='part-1', domain_name='test')
            session.add_all([project, participant])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.list_algorithms')
    def test_get_participant_algorithms(self, mock_list_algorithms):
        parameter = ParseDict({'variables': [{'name': 'BATCH_SIZE', 'value': '128'}]}, AlgorithmParameter())
        participant_algorithms = [
            AlgorithmPb(uuid='algo-uuid-1',
                        name='test-algo-1',
                        version=1,
                        type=AlgorithmType.NN_VERTICAL.name,
                        source=Source.USER.name,
                        parameter=parameter,
                        comment='comment-1',
                        created_at=1326542405,
                        updated_at=1326542405),
            AlgorithmPb(uuid='algo-uuid-2',
                        name='test-algo-2',
                        version=2,
                        type=AlgorithmType.TREE_VERTICAL.name,
                        source=Source.THIRD_PARTY.name,
                        parameter=parameter,
                        comment='comment-2',
                        created_at=1326542405,
                        updated_at=1326542405)
        ]
        mock_list_algorithms.return_value = ListAlgorithmsResponse(algorithms=participant_algorithms)
        resp = self.get_helper('/api/v2/projects/1/participants/1/algorithms?algorithm_project_uuid=uuid')
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['uuid'], 'algo-uuid-1')
        self.assertEqual(data[0]['version'], 1)
        self.assertEqual(data[0]['comment'], 'comment-1')
        self.assertEqual(data[0]['participant_id'], 1)
        self.assertEqual(data[1]['name'], 'test-algo-2')
        self.assertEqual(data[1]['type'], 'TREE_VERTICAL')
        self.assertEqual(data[1]['source'], 'THIRD_PARTY')
        self.assertEqual(data[1]['participant_id'], 1)


class ParticipantAlgorithmApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project-1')
            participant = Participant(id=1, name='part-1', domain_name='test')
            algorithm = Algorithm(id=1,
                                  uuid='algo-uuid-1',
                                  name='test-algo-1',
                                  version=1,
                                  type=AlgorithmType.NN_VERTICAL,
                                  source=Source.USER,
                                  created_at=datetime(2012, 1, 14, 12, 0, 5),
                                  updated_at=datetime(2012, 1, 14, 12, 0, 5))
            session.add_all([project, participant, algorithm])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.get_algorithm')
    def test_get_participant_algorithm(self, mock_get_algorithm):
        with db.session_scope() as session:
            algo = session.query(Algorithm).get(1)
        mock_get_algorithm.return_value = AlgorithmPb(uuid=algo.uuid,
                                                      name=algo.name,
                                                      version=algo.version,
                                                      type=algo.type.name,
                                                      source=algo.source.name,
                                                      comment=algo.comment)
        resp = self.get_helper('/api/v2/projects/1/participants/1/algorithms/algo-uuid-1')
        data = self.get_response_data(resp)
        self.assertEqual(data['name'], 'test-algo-1')
        self.assertEqual(data['version'], 1)
        self.assertEqual(data['type'], 'NN_VERTICAL')
        self.assertEqual(data['source'], 'USER')


class ParticipantAlgorithmFilesApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project-1')
            participant = Participant(id=1, name='part-1', domain_name='test')
            path = generate_algorithm_files()
            algorithm = Algorithm(id=1, uuid='algo-uuid-1', name='test-algo-1', path=path)
            session.add_all([project, participant, algorithm])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.get_algorithm')
    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.get_algorithm_files')
    def test_get_participant_algorithm_tree(self, mock_get_algorithm_files, mock_get_algorithm):
        with db.session_scope() as session:
            algo = session.query(Algorithm).get(1)
            mock_get_algorithm.return_value = algo.to_proto()
        data_iterator = AlgorithmSender().make_algorithm_iterator(algo.path)
        mock_get_algorithm_files.return_value = data_iterator
        with tempfile.TemporaryDirectory() as temp_dir:
            Envs.STORAGE_ROOT = temp_dir
            resp = self.get_helper('/api/v2/projects/1/participants/1/algorithms/algo-uuid-1/tree')
            data = self.get_response_data(resp)
            data = sorted(data, key=lambda d: d['filename'])
            self.assertPartiallyEqual(data[1], {
                'filename': 'leader',
                'path': 'leader',
                'is_directory': True
            },
                                      ignore_fields=['size', 'mtime', 'files'])
            self.assertPartiallyEqual(data[1]['files'][0], {
                'filename': 'main.py',
                'path': 'leader/main.py',
                'is_directory': False
            },
                                      ignore_fields=['size', 'mtime', 'files'])

    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.get_algorithm')
    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.get_algorithm_files')
    def test_get_participant_algorithm_files(self, mock_get_algorithm_files, mock_get_algorithm):
        with db.session_scope() as session:
            algo = session.query(Algorithm).get(1)
            mock_get_algorithm.return_value = algo.to_proto()
        data_iterator = AlgorithmSender().make_algorithm_iterator(algo.path)
        mock_get_algorithm_files.return_value = data_iterator
        with tempfile.TemporaryDirectory() as temp_dir:
            Envs.STORAGE_ROOT = temp_dir
            resp = self.get_helper('/api/v2/projects/1/participants/1/algorithms/algo-uuid-1/files?path=..')
            self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
            resp = self.get_helper('/api/v2/projects/1/participants/1/algorithms/algo-uuid-1/files?path=leader')
            self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
            resp = self.get_helper(
                '/api/v2/projects/1/participants/1/algorithms/algo-uuid-1/files?path=leader/config.py')
            self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
            resp = self.get_helper('/api/v2/projects/1/participants/1/algorithms/algo-uuid-1/files?path=leader/main.py')
            self.assertEqual(resp.status_code, HTTPStatus.OK)
            self.assertResponseDataEqual(resp, {'content': 'import tensorflow', 'path': 'leader/main.py'})


class FetchAlgorithmApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant = Participant(id=1, name='part', domain_name='part-test.com')
            project_participant = ProjectParticipant(id=1, project_id=1, participant_id=1)
            algorithm = Algorithm(id=1, uuid='uuid', name='algo', project_id=1, source=Source.USER)
            session.add_all([project, participant, project_participant, algorithm])
            session.commit()

    def test_get_algorithm(self):
        resp = self.get_helper('/api/v2/projects/1/algorithms/uuid')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(data['name'], 'algo')

    @patch('fedlearner_webconsole.algorithm.fetcher.AlgorithmFetcher.get_algorithm_from_participant')
    def test_get_algorithm_from_participant(self, mock_get_algorithm_from_participant):
        mock_get_algorithm_from_participant.return_value = AlgorithmPb(name='peer-algo')
        resp = self.get_helper('/api/v2/projects/1/algorithms/uuid-1')
        mock_get_algorithm_from_participant.assert_called_with(algorithm_uuid='uuid-1', participant_id=1)
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(data['name'], 'peer-algo')


class UpdatePresetAlgorithmApiTest(BaseTestCase):

    def test_update_preset_algorithms(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            Envs.STORAGE_ROOT = temp_dir
            self.signin_as_admin()
            resp = self.post_helper('/api/v2/preset_algorithms:update')
            self.assertEqual(resp.status_code, HTTPStatus.OK)
            data = self.get_response_data(resp)
            self.assertEqual(sorted([d['name'] for d in data]), ['e2e_test', 'horizontal_e2e_test', 'secure_boost'])
            with db.session_scope() as session:
                algo_project1 = session.query(AlgorithmProject).filter_by(name='e2e_test').first()
                self.assertIsNotNone(algo_project1)
                self.assertEqual(algo_project1.type, AlgorithmType.NN_VERTICAL)
                self.assertEqual(algo_project1.source, Source.PRESET)
                algo_project2 = session.query(AlgorithmProject).filter_by(name='secure_boost').first()
                self.assertIsNotNone(algo_project2)
                self.assertEqual(algo_project2.type, AlgorithmType.TREE_VERTICAL)
                self.assertEqual(algo_project2.source, Source.PRESET)
                algo1 = session.query(Algorithm).filter_by(name='e2e_test').first()
                self.assertIsNotNone(algo1)
                self.assertEqual(algo1.type, AlgorithmType.NN_VERTICAL)
                self.assertEqual(algo1.source, Source.PRESET)
                self.assertEqual(algo1.algorithm_project_id, algo_project1.id)
                self.assertTrue(os.path.exists(os.path.join(algo1.path, 'follower/config.py')))
                self.assertTrue(os.path.exists(os.path.join(algo1.path, 'leader/config.py')))
                algo2 = session.query(Algorithm).filter_by(name='secure_boost').first()
                self.assertIsNotNone(algo2)
                self.assertEqual(algo2.type, AlgorithmType.TREE_VERTICAL)
                self.assertEqual(algo2.source, Source.PRESET)
                self.assertEqual(algo2.algorithm_project_id, algo_project2.id)


class ReleaseAlgorithmApiTest(BaseTestCase):

    @patch('fedlearner_webconsole.algorithm.apis.algorithm_path')
    @patch('fedlearner_webconsole.algorithm.service.Algorithm')
    def test_release_algorithm_with_exceptions(self, mock_algorithm, mock_algorithm_path):
        path = generate_algorithm_files()
        with db.session_scope() as session:
            algo_project = AlgorithmProject(name='test-algo', path=path)
            session.add(algo_project)
            session.commit()
            self.assertEqual(algo_project.release_status, ReleaseStatus.UNRELEASED)
        Envs.STORAGE_ROOT = tempfile.mkdtemp()
        algorithm_path = os.path.join(Envs.STORAGE_ROOT, 'algorithms', 'test_with_exceptions')
        mock_algorithm_path.return_value = algorithm_path
        mock_algorithm.side_effect = Exception()
        self.post_helper(f'/api/v2/algorithm_projects/{algo_project.id}:release', {})
        self.assertFalse(os.path.exists(algorithm_path))

    def test_release_algorithm(self):
        path = generate_algorithm_files()
        with db.session_scope() as session:
            algo_project = AlgorithmProject(name='test-algo', path=path)
            session.add(algo_project)
            session.commit()
            self.assertEqual(algo_project.release_status, ReleaseStatus.UNRELEASED)
        Envs.STORAGE_ROOT = tempfile.mkdtemp()
        resp = self.post_helper(f'/api/v2/algorithm_projects/{algo_project.id}:release', {})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).get(1)
            algo = algo_project.algorithms[0]
            self.assertEqual(algo_project.release_status, ReleaseStatus.RELEASED)
            self.assertEqual(algo.name, 'test-algo')
            self.assertEqual(algo.version, 1)
            self.assertTrue(algo.path.startswith(Envs.STORAGE_ROOT))
        with open(os.path.join(algo.path, 'leader', 'main.py'), 'r', encoding='utf-8') as fin:
            self.assertEqual(fin.read(), 'import tensorflow')
        self.assertTrue(os.path.exists(os.path.join(algo.path, 'follower', 'main.py')))
        resp = self.post_helper(f'/api/v2/algorithm_projects/{algo_project.id}:release', data={'comment': 'comment'})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).get(1)
            self.assertEqual(algo_project.release_status, ReleaseStatus.RELEASED)
            self.assertEqual(len(algo_project.algorithms), 2)
            algo = algo_project.algorithms[0]
            self.assertEqual(algo.name, 'test-algo')
            self.assertEqual(algo.comment, 'comment')
            self.assertEqual(algo.version, 2)

    def test_release_algorithm_failed(self):
        path = generate_algorithm_files()
        with db.session_scope() as session:
            algo_project = AlgorithmProject(name='test-algo', path=path, source=Source.THIRD_PARTY)
            session.add(algo_project)
            session.commit()
            self.assertEqual(algo_project.release_status, ReleaseStatus.UNRELEASED)
        Envs.STORAGE_ROOT = tempfile.mkdtemp()
        resp = self.post_helper(f'/api/v2/algorithm_projects/{algo_project.id}:release', {})
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)


class PublishAlgorithmApiTest(BaseTestCase):

    def test_publish_algorithm(self):
        with db.session_scope() as session:
            project = Project(id=1, name='test-project')
            algo_project = AlgorithmProject(id=1,
                                            project_id=1,
                                            name='test-algo-project',
                                            publish_status=PublishStatus.UNPUBLISHED)
            algo = Algorithm(id=1,
                             project_id=1,
                             name='test-algo',
                             algorithm_project_id=1,
                             publish_status=PublishStatus.UNPUBLISHED)
            session.add_all([project, algo_project, algo])
            session.commit()
        resp = self.post_helper('/api/v2/projects/1/algorithms/1:publish')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(data['status'], PublishStatus.PUBLISHED.name)
        with db.session_scope() as session:
            algo = session.query(Algorithm).get(1)
            self.assertEqual(algo.publish_status, PublishStatus.PUBLISHED)
            algo_project = session.query(AlgorithmProject).get(1)
            self.assertEqual(algo_project.publish_status, PublishStatus.PUBLISHED)


class UnpublishAlgorithmApiTest(BaseTestCase):

    def test_unpublish_algorithm(self):
        with db.session_scope() as session:
            project = Project(id=1, name='test-project')
            algo_project = AlgorithmProject(id=1,
                                            project_id=1,
                                            name='test-algo-project',
                                            publish_status=PublishStatus.PUBLISHED)
            algo1 = Algorithm(id=1,
                              project_id=1,
                              algorithm_project_id=1,
                              name='test-algo-1',
                              publish_status=PublishStatus.PUBLISHED)
            algo2 = Algorithm(id=2,
                              project_id=1,
                              algorithm_project_id=1,
                              name='test-algo-2',
                              publish_status=PublishStatus.PUBLISHED)
            session.add_all([project, algo_project, algo1, algo2])
            session.commit()
        resp = self.post_helper('/api/v2/projects/1/algorithms/1:unpublish')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(data['status'], PublishStatus.UNPUBLISHED.name)
        with db.session_scope() as session:
            algo = session.query(Algorithm).get(1)
            self.assertEqual(algo.publish_status, PublishStatus.UNPUBLISHED)
            algo_project = session.query(AlgorithmProject).get(1)
            self.assertEqual(algo_project.publish_status, PublishStatus.PUBLISHED)
        resp = self.post_helper('/api/v2/projects/1/algorithms/2:unpublish')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(data['status'], PublishStatus.UNPUBLISHED.name)
        with db.session_scope() as session:
            algo = session.query(Algorithm).get(2)
            self.assertEqual(algo.publish_status, PublishStatus.UNPUBLISHED)
            algo_project = session.query(AlgorithmProject).get(1)
            self.assertEqual(algo_project.publish_status, PublishStatus.UNPUBLISHED)


class PendingAlgorithmsApiTest(BaseTestCase):

    def test_get_pending_algorithms(self):
        with db.session_scope() as session:
            uuid = resource_uuid()
            algo_project = AlgorithmProject(name='test-algo', uuid=uuid)
            participant = Participant(name='test-part', domain_name='haha')
            session.add(algo_project)
            session.add(participant)
            session.flush()
            pending_algo_1 = PendingAlgorithm(name='test-algo-1',
                                              algorithm_project_uuid=uuid,
                                              project_id=1,
                                              created_at=datetime(2021, 12, 2, 0, 0),
                                              participant_id=participant.id)
            pending_algo_2 = PendingAlgorithm(name='test-algo-2', project_id=2, created_at=datetime(2021, 12, 2, 0, 1))
            pending_algo_3 = PendingAlgorithm(name='test-algo-3', project_id=2, deleted_at=datetime(2021, 12, 2))
            session.add_all([pending_algo_1, pending_algo_2, pending_algo_3])
            session.commit()
        resp = self.get_helper('/api/v2/projects/0/pending_algorithms')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'test-algo-2')
        resp = self.get_helper('/api/v2/projects/1/pending_algorithms')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 1)
        with db.session_scope() as session:
            algo_project = session.query(AlgorithmProject).filter_by(uuid=uuid).first()
        self.assertPartiallyEqual(
            data[0], {
                'name': 'test-algo-1',
                'project_id': 1,
                'algorithm_project_id': algo_project.id,
                'version': 0,
                'type': 'UNSPECIFIED',
                'path': '',
                'comment': '',
                'participant_id': participant.id,
                'participant_name': 'test-part'
            },
            ignore_fields=['id', 'algorithm_uuid', 'algorithm_project_uuid', 'created_at', 'updated_at', 'deleted_at'])


class AcceptPendingAlgorithmApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(name='test')
            session.add(project)
            session.flush()
            pending_algo = PendingAlgorithm(name='test-algo',
                                            version=2,
                                            project_id=project.id,
                                            algorithm_uuid=resource_uuid(),
                                            algorithm_project_uuid=resource_uuid(),
                                            type=AlgorithmType.NN_VERTICAL,
                                            participant_id=1)
            pending_algo.path = generate_algorithm_files()
            session.add(pending_algo)
            session.commit()

    @patch('fedlearner_webconsole.algorithm.service.Algorithm')
    @patch('fedlearner_webconsole.algorithm.service.AlgorithmProject')
    @patch('fedlearner_webconsole.algorithm.apis.algorithm_project_path')
    @patch('fedlearner_webconsole.algorithm.apis.algorithm_path')
    def test_accept_pending_algorithm_with_exceptions(self, mock_algorithm_path, mock_algorithm_project_path,
                                                      mock_algorithm, mock_algorithm_project):
        with db.session_scope() as session:
            pending_algo = session.query(PendingAlgorithm).filter_by(name='test-algo').first()
        with tempfile.TemporaryDirectory() as temp_dir:
            Envs.STORAGE_ROOT = temp_dir
            name = 'test_with_exceptions'
            algo_project_path = os.path.join(Envs.STORAGE_ROOT, 'algorithm_projects', name)
            mock_algorithm_project_path.return_value = algo_project_path
            algorithm_path = os.path.join(Envs.STORAGE_ROOT, 'algorithms', name)
            mock_algorithm_path.return_value = algorithm_path
            mock_algorithm.side_effect = Exception()
            mock_algorithm_project.side_effect = Exception()
            self.post_helper(f'/api/v2/projects/1/pending_algorithms/{pending_algo.id}:accept', data={'name': 'algo-1'})
            self.assertFalse(os.path.exists(algorithm_path))
            self.assertFalse(os.path.exists(algo_project_path))

    def test_accept_pending_algorithm(self):
        with db.session_scope() as session:
            pending_algo = session.query(PendingAlgorithm).filter_by(name='test-algo').first()
        with tempfile.TemporaryDirectory() as temp_dir:
            Envs.STORAGE_ROOT = temp_dir
            resp = self.post_helper(f'/api/v2/projects/1/pending_algorithms/{pending_algo.id}:accept',
                                    data={'name': 'algo-1'})
            self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
            with db.session_scope() as session:
                pending_algo = session.query(PendingAlgorithm).execution_options(include_deleted=True).filter_by(
                    name='test-algo').first()
                self.assertTrue(bool(pending_algo.deleted_at))
                algo_project = session.query(AlgorithmProject).filter_by(name='algo-1').first()
                self.assertEqual(algo_project.username, 'ada')
                self.assertEqual(algo_project.participant_id, pending_algo.participant_id)
                self.assertEqual(algo_project.latest_version, pending_algo.version)
                self.assertEqual(algo_project.type, pending_algo.type)
                self.assertEqual(algo_project.source, Source.THIRD_PARTY)
                self.assertEqual(len(algo_project.algorithms), 1)
                self.assertEqual(algo_project.release_status, ReleaseStatus.RELEASED)
                self.assertEqual(algo_project.algorithms[0].participant_id, pending_algo.participant_id)

    def test_accept_with_duplicate_uuid(self):
        uuid = resource_uuid()
        with tempfile.TemporaryDirectory() as temp_dir:
            Envs.STORAGE_ROOT = temp_dir
            with db.session_scope() as session:
                pending_algo = session.query(PendingAlgorithm).filter_by(name='test-algo').first()
                algorithm_project_uuid = pending_algo.algorithm_project_uuid
                algo_project_path = algorithm_project_path(Envs.STORAGE_ROOT, 'test-algo')
                algo_project = AlgorithmProject(name='test-algo-project',
                                                uuid=algorithm_project_uuid,
                                                path=algo_project_path,
                                                source=Source.THIRD_PARTY)
                algo_project.release_status = ReleaseStatus.RELEASED
                session.add(algo_project)
                session.commit()

            resp = self.post_helper(f'/api/v2/projects/1/pending_algorithms/{pending_algo.id}:accept',
                                    data={'name': 'test-algo-project'})
            self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
            with db.session_scope() as session:
                pending_algo = session.query(PendingAlgorithm).execution_options(include_deleted=True).filter_by(
                    name='test-algo').first()
                self.assertTrue(bool(pending_algo.deleted_at))
                algo_project = session.query(AlgorithmProject).filter_by(name='test-algo-project').first()
                self.assertEqual(algo_project.source, Source.THIRD_PARTY)
                self.assertEqual(len(algo_project.algorithms), 1)
                self.assertEqual(algo_project.release_status, ReleaseStatus.RELEASED)
                self.assertEqual(algo_project.uuid, pending_algo.algorithm_project_uuid)
                self.assertEqual(algo_project.algorithms[0].participant_id, pending_algo.participant_id)
                self.assertEqual(algo_project.algorithms[0].name, pending_algo.name)
                self.assertEqual(algo_project.algorithms[0].parameter, pending_algo.parameter)
                self.assertEqual(algo_project.algorithms[0].uuid, pending_algo.algorithm_uuid)
                self.assertEqual(sorted(os.listdir(algo_project.algorithms[0].path)), ['follower', 'leader'])


class PendingAlgorithmTreeApi(BaseTestCase):

    def test_get_tree(self):
        path = generate_algorithm_files()
        with db.session_scope() as session:
            pending_algo = PendingAlgorithm(name='test-algo', path=path)
            session.add(pending_algo)
            session.commit()
        resp = self.get_helper(f'/api/v2/projects/0/pending_algorithms/{pending_algo.id}/tree')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        data = sorted(data, key=lambda d: d['filename'])
        self.assertPartiallyEqual(data[1], {
            'filename': 'leader',
            'path': 'leader',
            'is_directory': True
        },
                                  ignore_fields=['size', 'mtime', 'files'])
        self.assertPartiallyEqual(data[1]['files'][0], {
            'filename': 'main.py',
            'path': 'leader/main.py',
            'is_directory': False
        },
                                  ignore_fields=['size', 'mtime', 'files'])


class PendingAlgorithmFilesApi(BaseTestCase):

    def test_get_file(self):
        path = generate_algorithm_files()
        with db.session_scope() as session:
            pending_algo = PendingAlgorithm(name='test-algo', path=path)
            session.add(pending_algo)
            session.commit()
        resp = self.get_helper(f'/api/v2/projects/0/pending_algorithms/{pending_algo.id}/files?path=leader/main.py')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {'content': 'import tensorflow', 'path': 'leader/main.py'})


if __name__ == '__main__':
    unittest.main()

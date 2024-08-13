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

import json
import unittest
import urllib.parse
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from envs import Envs
from fedlearner_webconsole.composer.models import SchedulerItem
from fedlearner_webconsole.db import db
from fedlearner_webconsole.k8s.models import Pod, PodState
from fedlearner_webconsole.mmgr.models import Model, ModelJobGroup
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.serving.models import ServingModel, ServingNegotiator
from fedlearner_webconsole.serving.remote import register_remote_serving
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from testing.common import BaseTestCase
from testing.fake_remote_serving import FakeRemoteServing


def _get_create_serving_service_input(name, project_id: int):
    res = {
        'name': name,
        'comment': 'test-comment-1',
        'cpu_per_instance': '2000m',
        'memory_per_instance': '2Gi',
        'instance_num': 3,
        'project_id': project_id,
        'is_local': True
    }
    return res


def _get_create_serving_service_input_v2(name, model_id: int):
    res = {
        'name': name,
        'comment': 'test-comment-1',
        'model_id': model_id,
        'is_local': True,
        'resource': {
            'cpu': '2',
            'memory': '2',
            'replicas': 3,
        }
    }
    return res


class ServingServicesApiV2Test(BaseTestCase):

    def setUp(self):
        super().setUp()
        # insert project
        with db.session_scope() as session:
            project = Project()
            project.name = 'test_project_name'
            session.add(project)
            session.flush([project])

            participant = Participant()
            participant.name = 'test_participant_name'
            participant.domain_name = 'test_domain_name'
            participant.project_id = project.id
            session.add(participant)
            session.flush([participant])

            project_participant = ProjectParticipant()
            project_participant.participant_id = participant.id
            project_participant.project_id = project.id
            session.add(project_participant)

            model_job_group = ModelJobGroup()
            session.add(model_job_group)
            session.flush([model_job_group])

            model_1 = Model()
            model_1.name = 'test_model_name_1'
            model_1.model_path = '/test_path_1/'
            model_1.uuid = 'test_uuid_1'
            model_1.project_id = project.id
            model_1.version = 1
            model_1.group_id = model_job_group.id
            model_2 = Model()
            model_2.name = 'test_model_name_2'
            model_2.model_path = '/test_path_2/'
            model_2.uuid = 'test_uuid_2'
            model_2.project_id = project.id
            model_2.version = 2
            model_2.group_id = model_job_group.id
            session.add_all([model_1, model_2])

            session.commit()
            self.project_id = project.id
            self.model_id_1 = model_1.id
            self.model_group_id = model_job_group.id
            self.model_id_2 = model_2.id

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_create_serving_service(self, mock_create_deployment: MagicMock):
        # create serving service
        name = 'test-serving-service-1'
        serving_service = _get_create_serving_service_input_v2(name, model_id=self.model_id_1)
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(HTTPStatus.CREATED, response.status_code)
        data = self.get_response_data(response)
        self.assertEqual(0, data['model_group_id'])
        serving_model_id = data['id']  # get id from create response

        # check db
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).get(serving_model_id)
            self.assertEqual(serving_model.name, name)
            self.assertEqual('/test_path_1/exported_models', serving_model.model_path)
            serving_deployment = serving_model.serving_deployment
            deployment_name_substr = f'serving-{serving_model_id}-'
            self.assertIn(deployment_name_substr, serving_deployment.deployment_name)
            self.assertEqual(serving_deployment.resource, json.dumps({
                'cpu': '2',
                'memory': '2',
                'replicas': 3,
            }))
            serving_negotiator = session.query(ServingNegotiator).filter_by(
                serving_model_id=serving_model_id).one_or_none()
            self.assertIsNotNone(serving_negotiator)
            self.assertEqual(serving_negotiator.project_id, self.project_id)

        mock_create_deployment.assert_called_once()

        # create same name
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        data = self.get_response_data(response)
        self.assertEqual(HTTPStatus.CONFLICT, response.status_code)
        self.assertIsNone(data)

        # resource format error
        serving_service['resource'] = {
            'cpu': 2,
            'memory': '2',
            'replicas': 3,
        }
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_code)

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_create_auto_update_serving_service(self, mock_create_deployment: MagicMock):
        # create serving service
        name = 'test-auto-update-1'
        serving_service = {
            'name': name,
            'comment': 'test-comment-1',
            'model_group_id': self.model_group_id,
            'is_local': True,
            'resource': {
                'cpu': '2',
                'memory': '2',
                'replicas': 3,
            }
        }
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(HTTPStatus.CREATED, response.status_code)
        data = self.get_response_data(response)
        self.assertEqual(self.model_id_2, data['model_id'])
        serving_model_id = data['id']  # get id from create response

        # check db
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).get(serving_model_id)
            self.assertEqual(serving_model.name, name)
            self.assertEqual('/test_path_2/exported_models', serving_model.model_path)

        mock_create_deployment.assert_called_once()

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_get_serving_services(self, mock_create_deployment: MagicMock):
        # create
        name1 = 'test-get-services-1'
        serving_service = _get_create_serving_service_input_v2(name1, model_id=self.model_id_1)
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(HTTPStatus.CREATED, response.status_code)
        name2 = 'test-get-services-2'
        serving_service = _get_create_serving_service_input_v2(name2, model_id=self.model_id_1)
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(HTTPStatus.CREATED, response.status_code)
        # get list
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services')
        data = self.get_response_data(response)
        self.assertEqual(2, len(data))
        self.assertIn(data[0]['name'], [name1, name2])
        self.assertIn(data[1]['name'], [name1, name2])
        self.assertEqual(self.project_id, data[0]['project_id'])
        self.assertEqual('LOADING', data[0]['status'])
        self.assertEqual('UNKNOWN', data[0]['instance_num_status'])

        # get with filter
        filter_param = urllib.parse.quote(f'(name="{name1}")')
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services?filter={filter_param}')
        data = self.get_response_data(response)
        self.assertEqual(1, len(data))

        filter_param = urllib.parse.quote('(name="test-get-services-3")')  # test not found
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services?filter={filter_param}')
        data = self.get_response_data(response)
        self.assertEqual(0, len(data))

        filter_param = urllib.parse.quote('(keyword~="services-1")')
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services?filter={filter_param}')
        data = self.get_response_data(response)
        self.assertEqual(1, len(data))

        sorter_param = urllib.parse.quote('created_at asc')
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services?order_by={sorter_param}')
        data = self.get_response_data(response)
        self.assertEqual(2, len(data))
        self.assertEqual([name1, name2], [data[0]['name'], data[1]['name']])

        sorter_param = urllib.parse.quote('created_at desc')
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services?order_by={sorter_param}')
        data = self.get_response_data(response)
        self.assertEqual(2, len(data))
        self.assertEqual([name2, name1], [data[0]['name'], data[1]['name']])

        sorter_param = urllib.parse.quote('something_unsupported desc')
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services?order_by={sorter_param}')
        data = self.get_response_data(response)
        self.assertIsNone(data)

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.get_pods_info')
    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_get_serving_service(self, mock_create_deployment: MagicMock, mock_get_pods_info):
        test_datetime = datetime(2022, 1, 1, 8, 8, 8, tzinfo=timezone.utc)
        fake_pods = [
            Pod(name='pod0', state=PodState.FAILED, creation_timestamp=to_timestamp(test_datetime)),
            Pod(name='pod1', state=PodState.RUNNING, creation_timestamp=to_timestamp(test_datetime) - 1),
            Pod(name='pod2', state=PodState.SUCCEEDED, creation_timestamp=to_timestamp(test_datetime) + 1)
        ]
        mock_get_pods_info.return_value = fake_pods
        # create
        name1 = 'test-get-services-1'
        serving_service = _get_create_serving_service_input_v2(name1, model_id=self.model_id_1)
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(HTTPStatus.CREATED, response.status_code)
        data = self.get_response_data(response)
        serving_service_id = data['id']
        # get one
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services/{serving_service_id}')
        data = self.get_response_data(response)
        self.assertEqual(name1, data['name'])
        self.assertEqual({'cpu': '2', 'memory': '2', 'replicas': 3}, data['resource'])
        self.assertEqual(f'/api/v2/projects/{self.project_id}/serving_services/{serving_service_id}/inference',
                         data['endpoint'])
        self.assertEqual('UNKNOWN', data['instance_num_status'])
        self.assertEqual(['pod0', 'pod1', 'pod2'], [x['name'] for x in data['instances']])
        sorter_param = urllib.parse.quote('created_at asc')
        response = self.get_helper(
            f'/api/v2/projects/{self.project_id}/serving_services/{serving_service_id}?order_by={sorter_param}')
        data = self.get_response_data(response)
        self.assertEqual(3, len(data['instances']))
        self.assertEqual(['pod1', 'pod0', 'pod2'], [x['name'] for x in data['instances']])
        sorter_param = urllib.parse.quote('created_at desc')
        response = self.get_helper(
            f'/api/v2/projects/{self.project_id}/serving_services/{serving_service_id}?order_by={sorter_param}')
        data = self.get_response_data(response)
        self.assertEqual(3, len(data['instances']))
        self.assertEqual(['pod2', 'pod0', 'pod1'], [x['name'] for x in data['instances']])

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_update_serving_service(self, mock_create_deployment: MagicMock):
        # create
        name = 'test-update-service-1'
        serving_service = _get_create_serving_service_input_v2(name, model_id=self.model_id_1)
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        data = self.get_response_data(response)
        service_id = data['id']  # get id from create response
        # update comments
        new_comment = 'test-comment-2'
        serving_service = {
            'comment': new_comment,
            'resource': {
                'cpu': '2',
                'memory': '2',
                'replicas': 3,
            }
        }
        response = self.patch_helper(f'/api/v2/projects/{self.project_id}/serving_services/{service_id}',
                                     data=serving_service)
        data = self.get_response_data(response)
        self.assertEqual(data['comment'], new_comment)

        # change from model_id to model_group_id
        serving_service = {
            'model_group_id': self.model_group_id,
        }
        response = self.patch_helper(f'/api/v2/projects/{self.project_id}/serving_services/{service_id}',
                                     data=serving_service)
        data = self.get_response_data(response)
        self.assertEqual(self.model_id_2, data['model_id'])
        self.assertEqual(self.model_group_id, data['model_group_id'])
        # check db
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).get(service_id)
            self.assertEqual('/test_path_2/exported_models', serving_model.model_path)

        # change from model_group_id to model_id
        serving_service = {
            'model_id': self.model_id_1,
        }
        response = self.patch_helper(f'/api/v2/projects/{self.project_id}/serving_services/{service_id}',
                                     data=serving_service)
        data = self.get_response_data(response)
        self.assertEqual(0, data['model_group_id'])
        self.assertEqual(self.model_id_1, data['model_id'])
        # check db
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).get(service_id)
            self.assertEqual('/test_path_1/exported_models', serving_model.model_path)

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    @patch('fedlearner_webconsole.serving.services.k8s_client')
    def test_delete_serving_service(self, mock_create_deployment: MagicMock, mock_k8s_client: MagicMock):
        mock_k8s_client.delete_config_map = MagicMock()
        mock_k8s_client.delete_deployment = MagicMock()
        mock_k8s_client.delete_service = MagicMock()
        # create
        name = 'test-delete-service-1'
        serving_service = _get_create_serving_service_input_v2(name, model_id=self.model_id_1)
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        data = self.get_response_data(response)
        service_id = data['id']  # get id from create response
        # delete
        response = self.delete_helper(f'/api/v2/projects/{self.project_id}/serving_services/{service_id}')
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        # get
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services/{service_id}')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        data = self.get_response_data(response)
        self.assertIsNone(data)

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    @patch('fedlearner_webconsole.serving.services.k8s_client.get_pod_log')
    def test_get_serving_service_instance_log(self, mock_query_log: MagicMock, mock_create_deployment: MagicMock):
        # create
        name = 'test-get-service-instance-log-1'
        serving_service = _get_create_serving_service_input_v2(name, model_id=self.model_id_1)
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        mock_create_deployment.assert_called_once()
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        data = self.get_response_data(response)
        service_id = data['id']  # get id from create response
        # get
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services/{service_id}')
        data = self.get_response_data(response)
        self.assertEqual(len(data['instances']), 1)
        instance_name = data['instances'][0]['name']  # get id from create response
        # get log
        mock_query_log.return_value = ['test', 'hello']
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services/{service_id}'
                                   f'/instances/{instance_name}/log?tail_lines={500}')
        mock_query_log.assert_called_once_with(instance_name, namespace=Envs.K8S_NAMESPACE, tail_lines=500)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertCountEqual(self.get_response_data(response), ['test', 'hello'])

    @patch('fedlearner_webconsole.utils.flask_utils.get_current_sso', MagicMock(return_value='test-sso'))
    def test_remote_platform_serving_service(self):
        reckon_remote_serving = FakeRemoteServing()
        register_remote_serving(FakeRemoteServing.SERVING_PLATFORM, reckon_remote_serving)
        # get
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services/remote_platforms')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(1, len(data))
        self.assertEqual(FakeRemoteServing.SERVING_PLATFORM, data[0]['platform'])
        self.assertEqual('', data[0]['payload'])

        # create serving service
        name = 'test-remote-serving-1'
        serving_service = {
            'name': name,
            'model_group_id': self.model_group_id,
            'is_local': True,
            'remote_platform': {
                'platform': FakeRemoteServing.SERVING_PLATFORM,
                'payload': 'test-payload',
            }
        }
        response = self.post_helper(f'/api/v2/projects/{self.project_id}/serving_services', data=serving_service)
        self.assertEqual(HTTPStatus.CREATED, response.status_code)
        data = self.get_response_data(response)
        self.assertEqual({'platform': 'unittest_mock', 'payload': 'test-payload'}, data['remote_platform'])
        service_id = data['id']

        # get list
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services')
        data = self.get_response_data(response)
        self.assertEqual(1, len(data))
        self.assertEqual('AVAILABLE', data[0]['status'])
        self.assertTrue(data[0]['support_inference'])

        # get one
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services/{service_id}')
        data = self.get_response_data(response)
        self.assertEqual('test_deploy_url', data['endpoint'])
        self.assertEqual('AVAILABLE', data['status'])
        self.assertTrue(data['support_inference'])
        self.assertEqual({'platform': 'unittest_mock', 'payload': 'test-payload'}, data['remote_platform'])

        # change from model_group_id to model_id
        serving_service = {
            'model_id': self.model_id_1,
        }
        response = self.patch_helper(f'/api/v2/projects/{self.project_id}/serving_services/{service_id}',
                                     data=serving_service)
        data = self.get_response_data(response)
        self.assertEqual(0, data['model_group_id'])
        self.assertEqual(self.model_id_1, data['model_id'])
        # check db
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).get(service_id)
            self.assertEqual('/test_path_1/exported_models', serving_model.model_path)
            item = session.query(SchedulerItem.id).filter(SchedulerItem.name.like(f'%{name}%')).first()
            self.assertIsNone(item)

        # delete
        response = self.delete_helper(f'/api/v2/projects/{self.project_id}/serving_services/{service_id}')
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        response = self.get_helper(f'/api/v2/projects/{self.project_id}/serving_services/{service_id}')
        data = self.get_response_data(response)
        self.assertIsNone(data)


if __name__ == '__main__':
    unittest.main()

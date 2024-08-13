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
import os
import unittest
from unittest.mock import MagicMock, patch, call

from google.protobuf import text_format
from google.protobuf.json_format import MessageToDict
from tensorflow.core.protobuf import saved_model_pb2
from envs import Envs
from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.exceptions import NotFoundException, InvalidArgumentException
from fedlearner_webconsole.initial_db import initial_db
from fedlearner_webconsole.mmgr.models import Model, ModelJobGroup, ModelType
from fedlearner_webconsole.proto import serving_pb2
from fedlearner_webconsole.serving.remote import register_remote_serving
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.serving.models import ServingDeployment, ServingModel, ServingNegotiator, ServingModelStatus
from fedlearner_webconsole.serving.services import SavedModelService, ServingDeploymentService, ServingModelService

from testing.common import BaseTestCase
from testing.fake_remote_serving import FakeRemoteServing
from testing.no_web_server_test_case import NoWebServerTestCase


class ServingDeploymentServiceTest(NoWebServerTestCase):

    def setUp(self) -> None:
        super().setUp()
        initial_db()
        with db.session_scope() as session:

            project = Project()
            project.name = 'test_project_name'
            session.add(project)
            session.flush([project])

            serving_deployment = ServingDeployment()
            serving_deployment.deployment_name = 'test_deployment_name'
            serving_deployment.project_id = project.id
            serving_deployment.resource = json.dumps({'cpu': '4000m', 'memory': '8Gi', 'replicas': 3})
            session.add(serving_deployment)
            session.flush([serving_deployment])

            serving_model = ServingModel()
            serving_model.project_id = project.id
            serving_model.serving_deployment_id = serving_deployment.id
            session.add(serving_model)

            session.commit()

        self.serving_model_id = serving_model.id

    @patch('fedlearner_webconsole.serving.services.k8s_client')
    def test_create_deployment(self, mock_k8s_client: MagicMock):
        mock_k8s_client.create_or_update_app = MagicMock()
        mock_k8s_client.create_or_update_config_map = MagicMock()
        mock_k8s_client.create_or_update_service = MagicMock()

        with db.session_scope() as session:
            # This is the best practices for using serving_model_id to interact with two session.
            serving_model = session.query(ServingModel).get(self.serving_model_id)
            service = ServingDeploymentService(session)
            service.create_or_update_deployment(serving_model)

        mock_k8s_client.create_or_update_config_map.assert_called_once()
        mock_k8s_client.create_or_update_service.assert_called_once()
        mock_k8s_client.create_or_update_app.assert_called_once()

    @patch('fedlearner_webconsole.serving.services.k8s_client')
    def test_delete_deployment(self, mock_k8s_client: MagicMock):
        mock_k8s_client.delete_app = MagicMock()
        mock_k8s_client.delete_config_map = MagicMock()
        mock_k8s_client.delete_service = MagicMock()

        with db.session_scope() as session:
            # This is the best practices for using serving_model_id to interact with two session.
            serving_model = session.query(ServingModel).get(self.serving_model_id)
            service = ServingDeploymentService(session)
            service.delete_deployment(serving_model)

        mock_k8s_client.delete_app.assert_has_calls([
            call(app_name=serving_model.serving_deployment.deployment_name,
                 group='apps',
                 version='v1',
                 plural='deployments',
                 namespace=Envs.K8S_NAMESPACE),
        ])
        mock_k8s_client.delete_config_map.assert_called_once_with(
            name=f'{serving_model.serving_deployment.deployment_name}-config', namespace=Envs.K8S_NAMESPACE)
        mock_k8s_client.delete_service.assert_called_once_with(name=serving_model.serving_deployment.deployment_name,
                                                               namespace=Envs.K8S_NAMESPACE)

    def test_get_pods_info(self):
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).filter_by(id=self.serving_model_id).one()
            deployment_name = serving_model.serving_deployment.deployment_name

        info = ServingDeploymentService.get_pods_info(deployment_name)
        self.assertEqual(len(info), 1)


class SavedModelServiceTest(NoWebServerTestCase):

    def setUp(self) -> None:
        super().setUp()

        with open(os.path.join(Envs.BASE_DIR, 'testing/test_data/saved_model.pbtxt'), 'rt', encoding='utf-8') as f:
            self.saved_model_text = f.read()

        self.saved_model_message = text_format.Parse(self.saved_model_text, saved_model_pb2.SavedModel())
        self.graph = self.saved_model_message.meta_graphs[0].graph_def

    def test_get_nodes_from_graph(self):
        parse_example_node = SavedModelService.get_nodes_from_graph(
            self.graph, ['ParseExample/ParseExample'])['ParseExample/ParseExample']
        self.assertEqual(parse_example_node.name, 'ParseExample/ParseExample')
        self.assertEqual(parse_example_node.op, 'ParseExample')

        dense_nodes = SavedModelService.get_nodes_from_graph(
            self.graph, ['ParseExample/ParseExample/dense_keys_0', 'ParseExample/ParseExample/dense_keys_1'])
        self.assertEqual(len(dense_nodes), 2)

    def test_get_parse_example_details(self):
        signatures = SavedModelService.get_parse_example_details(self.saved_model_message.SerializeToString())
        self.assertCountEqual([i.name for i in signatures.inputs], ['example_id', 'x'])
        self.assertCountEqual([i.type for i in signatures.inputs], ['DT_STRING', 'DT_FLOAT'])
        self.assertCountEqual([i.dim for i in signatures.inputs], [[], [392]])


# Use BaseTestCase instead of NoWebServerTestCase to get system.variables.labels when generate deployment yaml
class ServingModelServiceTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        # insert project
        with db.session_scope() as session:
            project = Project()
            project.name = 'test_project_name'
            session.add(project)
            session.flush([project])

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
            model_2.project_id = project.id
            model_2.version = 2
            model_2.group_id = model_job_group.id

            session.add_all([model_1, model_2])
            session.commit()
            self.project_id = project.id
            self.model_1_id = model_1.id
            self.model_1_uuid = model_1.uuid
            self.model_2_id = model_2.id
            self.model_group_id = model_job_group.id

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_create_from_param(self, mock_create_deployment: MagicMock):
        name = 'test-serving-service-1'
        resource = serving_pb2.ServingServiceResource(
            cpu='1',
            memory='2',
            replicas=3,
        )
        param = {
            'model_id': self.model_1_id,
            'name': name,
            'comment': '',
            'resource': resource,
            'is_local': True,
        }
        with db.session_scope() as session:
            serving_model_service = ServingModelService(session)
            serving_model = serving_model_service.create_from_param(project_id=self.project_id,
                                                                    name=param['name'],
                                                                    is_local=param['is_local'],
                                                                    comment=param['comment'],
                                                                    model_id=param['model_id'],
                                                                    model_group_id=None,
                                                                    resource=param['resource'])
            session.commit()
            serving_model_id = serving_model.id

        # check db
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).get(serving_model_id)
            self.assertEqual(name, serving_model.name)
            self.assertEqual('/test_path_1/exported_models', serving_model.model_path)
            serving_deployment = serving_model.serving_deployment
            deployment_name_substr = f'serving-{serving_model_id}-'
            self.assertIn(deployment_name_substr, serving_deployment.deployment_name)
            self.assertEqual(
                serving_deployment.resource,
                json.dumps({
                    'cpu': resource.cpu,
                    'memory': resource.memory,
                    'replicas': resource.replicas,
                }))
            serving_negotiator = session.query(ServingNegotiator).filter_by(
                serving_model_id=serving_model_id).one_or_none()
            self.assertIsNotNone(serving_negotiator)
            self.assertEqual(serving_negotiator.project_id, self.project_id)

        mock_create_deployment.assert_called_once()

        name = 'test-auto-update-1'
        param = {
            'model_group_id': self.model_group_id,
            'name': name,
            'resource': resource,
            'is_local': True,
        }
        with db.session_scope() as session:
            serving_model_service = ServingModelService(session)
            serving_model = serving_model_service.create_from_param(project_id=self.project_id,
                                                                    name=param['name'],
                                                                    is_local=param['is_local'],
                                                                    comment=None,
                                                                    model_id=None,
                                                                    model_group_id=param['model_group_id'],
                                                                    resource=param['resource'])
            session.commit()
            serving_model_id = serving_model.id

        # check db
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).get(serving_model_id)
            self.assertEqual(self.model_2_id, serving_model.model_id)
            self.assertEqual('/test_path_2/exported_models', serving_model.model_path)

    @patch('fedlearner_webconsole.utils.flask_utils.get_current_user', MagicMock(return_value=User(username='test')))
    def test_create_remote_serving_from_param(self):
        reckon_remote_serving = FakeRemoteServing()
        register_remote_serving(FakeRemoteServing.SERVING_PLATFORM, reckon_remote_serving)
        name = 'test-remote-serving-1'
        remote_platform = serving_pb2.ServingServiceRemotePlatform(platform=FakeRemoteServing.SERVING_PLATFORM,
                                                                   payload='test-payload')
        with db.session_scope() as session:
            serving_model_service = ServingModelService(session)
            serving_model = serving_model_service.create_from_param(project_id=self.project_id,
                                                                    name=name,
                                                                    is_local=True,
                                                                    comment=None,
                                                                    model_id=None,
                                                                    model_group_id=self.model_group_id,
                                                                    resource=None,
                                                                    remote_platform=remote_platform)
            session.commit()
            serving_model_id = serving_model.id

        # check db
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).get(serving_model_id)
            self.assertEqual(FakeRemoteServing.DEPLOY_URL, serving_model.endpoint)
            deploy_platform = serving_pb2.RemoteDeployConfig(
                platform=FakeRemoteServing.SERVING_PLATFORM,
                payload='test-payload',
                deploy_id=1,
                deploy_name=f'privacy-platform-test-remote-serving-{serving_model_id}',
                model_src_path='',
            )
            self.assertEqual(json.dumps(MessageToDict(deploy_platform)),
                             serving_model.serving_deployment.deploy_platform)

    @patch('fedlearner_webconsole.utils.flask_utils.get_current_user', MagicMock(return_value=User(username='test')))
    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_get_detail(self, mock_create_deployment: MagicMock):
        name = 'test-serving-service-1'
        resource = serving_pb2.ServingServiceResource(
            cpu='1',
            memory='2',
            replicas=3,
        )
        param = {
            'model_id': self.model_1_id,
            'name': name,
            'comment': '',
            'resource': resource,
            'is_local': False,
        }
        with db.session_scope() as session:
            serving_model_service = ServingModelService(session)
            serving_model = serving_model_service.create_from_param(project_id=self.project_id,
                                                                    name=param['name'],
                                                                    is_local=param['is_local'],
                                                                    comment=param['comment'],
                                                                    model_id=param['model_id'],
                                                                    model_group_id=None,
                                                                    resource=param['resource'])
            detail = serving_model_service.get_serving_service_detail(serving_model.id, serving_model.project_id)
            self.assertEqual(name, detail.name)
            self.assertEqual(ServingModelStatus.PENDING_ACCEPT.name, detail.status)
            try:
                serving_model_service.get_serving_service_detail(serving_model.id + 1)
            except NotFoundException:
                pass
            try:
                serving_model_service.get_serving_service_detail(serving_model.id, serving_model.project_id + 1)
            except NotFoundException:
                pass

        # get remote serving detail
        name = 'test-remote-serving-1'
        reckon_remote_serving = FakeRemoteServing()
        register_remote_serving(FakeRemoteServing.SERVING_PLATFORM, reckon_remote_serving)
        remote_platform = serving_pb2.ServingServiceRemotePlatform(platform=FakeRemoteServing.SERVING_PLATFORM,
                                                                   payload='test-payload')
        with db.session_scope() as session:
            serving_model_service = ServingModelService(session)
            serving_model = serving_model_service.create_from_param(project_id=self.project_id,
                                                                    name=name,
                                                                    is_local=False,
                                                                    comment=None,
                                                                    model_id=self.model_1_id,
                                                                    model_group_id=None,
                                                                    resource=None,
                                                                    remote_platform=remote_platform)
            detail = serving_model_service.get_serving_service_detail(serving_model.id, serving_model.project_id)
            expected_detail = serving_pb2.ServingServiceDetail(id=serving_model.id,
                                                               project_id=self.project_id,
                                                               name=name,
                                                               model_id=self.model_1_id,
                                                               model_type=ModelType.NN_MODEL.name,
                                                               is_local=False,
                                                               endpoint='test_deploy_url',
                                                               instance_num_status='UNKNOWN',
                                                               status=ServingModelStatus.AVAILABLE.name,
                                                               support_inference=True)
            expected_detail.remote_platform.CopyFrom(
                serving_pb2.ServingServiceRemotePlatform(
                    platform='unittest_mock',
                    payload='test-payload',
                ))
            self.assertPartiallyEqual(to_dict(expected_detail),
                                      to_dict(detail),
                                      ignore_fields=['created_at', 'updated_at'])

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_set_ref(self, mock_create_deployment: MagicMock):
        name = 'test-serving-service-1'
        resource = serving_pb2.ServingServiceResource(
            cpu='1',
            memory='2',
            replicas=3,
        )
        param = {
            'model_id': self.model_1_id,
            'name': name,
            'comment': '',
            'resource': resource,
            'is_local': False,
        }
        with db.session_scope() as session:
            serving_model_service = ServingModelService(session)
            serving_model = serving_model_service.create_from_param(project_id=self.project_id,
                                                                    name=param['name'],
                                                                    is_local=param['is_local'],
                                                                    comment=param['comment'],
                                                                    model_id=param['model_id'],
                                                                    model_group_id=None,
                                                                    resource=param['resource'])
            serving_service = serving_model.to_serving_service()
            self.assertTrue(serving_service.is_local)  # default value
            serving_model_service = ServingModelService(session)
            serving_model_service.set_resource_and_status_on_ref(serving_service, serving_model)
            serving_model_service.set_is_local_on_ref(serving_service, serving_model)
            self.assertEqual('UNKNOWN', serving_service.instance_num_status)
            self.assertEqual('1', serving_service.resource.cpu)
            self.assertEqual('2', serving_service.resource.memory)
            self.assertEqual(3, serving_service.resource.replicas)
            self.assertFalse(serving_service.is_local)

    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_update_model(self, mock_create_deployment: MagicMock):
        resource = serving_pb2.ServingServiceResource(
            cpu='1',
            memory='2',
            replicas=3,
        )
        with db.session_scope() as session:
            serving_model_service = ServingModelService(session)
            serving_model = serving_model_service.create_from_param(project_id=self.project_id,
                                                                    name='test-serving-service-1',
                                                                    is_local=True,
                                                                    comment='',
                                                                    model_id=self.model_1_id,
                                                                    model_group_id=None,
                                                                    resource=resource)

            need_update = serving_model_service.update_model(model_id=None,
                                                             model_group_id=self.model_group_id,
                                                             serving_model=serving_model)
            self.assertEqual(True, need_update)
            self.assertEqual(self.model_2_id, serving_model.model_id)

            need_update = serving_model_service.update_model(model_id=self.model_2_id,
                                                             model_group_id=self.model_group_id,
                                                             serving_model=serving_model)
            self.assertEqual(False, need_update)
            self.assertEqual(self.model_2_id, serving_model.model_id)
            self.assertIsNone(serving_model.model_group_id)

            need_update = serving_model_service.update_model(model_id=self.model_1_id,
                                                             model_group_id=self.model_group_id,
                                                             serving_model=serving_model)
            self.assertEqual(True, need_update)
            self.assertEqual(self.model_1_id, serving_model.model_id)
            self.assertIsNone(serving_model.model_group_id)

            serving_model = serving_model_service.create_from_param(project_id=self.project_id,
                                                                    name='test-serving-service-2',
                                                                    is_local=False,
                                                                    comment='',
                                                                    model_id=self.model_1_id,
                                                                    model_group_id=None,
                                                                    resource=resource)
            with self.assertRaises(InvalidArgumentException):
                serving_model_service.update_model(model_id=None,
                                                   model_group_id=self.model_group_id,
                                                   serving_model=serving_model)

    @patch('fedlearner_webconsole.utils.flask_utils.get_current_user', MagicMock(return_value=User(username='test')))
    @patch('fedlearner_webconsole.serving.services.k8s_client')
    @patch('fedlearner_webconsole.serving.services.ServingDeploymentService.create_or_update_deployment')
    def test_delete_serving(self, mock_create_deployment: MagicMock, mock_k8s_client: MagicMock):
        mock_k8s_client.delete_config_map = MagicMock()
        mock_k8s_client.delete_app = MagicMock()
        mock_k8s_client.delete_service = MagicMock()
        # delete serving inside platform
        resource = serving_pb2.ServingServiceResource(
            cpu='1',
            memory='2',
            replicas=3,
        )
        with db.session_scope() as session:
            serving_model_service = ServingModelService(session)
            serving_model = serving_model_service.create_from_param(project_id=self.project_id,
                                                                    name='test-serving-service-1',
                                                                    is_local=True,
                                                                    comment='',
                                                                    model_id=self.model_1_id,
                                                                    model_group_id=None,
                                                                    resource=resource)
            serving_model_id = serving_model.id
            serving_deployment_id = serving_model.serving_deployment_id
            serving_model_service.delete_serving_service(serving_model)
        mock_k8s_client.delete_config_map.assert_called_once()
        mock_k8s_client.delete_app.assert_called_once()
        mock_k8s_client.delete_service.assert_called_once()
        # check db
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).get(serving_model_id)
            self.assertIsNone(serving_model)
            serving_deployment = session.query(ServingDeployment).get(serving_deployment_id)
            self.assertIsNone(serving_deployment)
            negotiator = session.query(ServingNegotiator).filter_by(serving_model_id=serving_model_id).one_or_none()
            self.assertIsNone(negotiator)

        # delete remote serving
        reckon_remote_serving = FakeRemoteServing()
        register_remote_serving(FakeRemoteServing.SERVING_PLATFORM, reckon_remote_serving)
        remote_platform = serving_pb2.ServingServiceRemotePlatform(platform=FakeRemoteServing.SERVING_PLATFORM,
                                                                   payload='test-payload')
        with db.session_scope() as session:
            serving_model_service = ServingModelService(session)
            serving_model = serving_model_service.create_from_param(project_id=self.project_id,
                                                                    name='test-remote-serving-1',
                                                                    is_local=True,
                                                                    comment=None,
                                                                    model_id=None,
                                                                    model_group_id=self.model_group_id,
                                                                    resource=None,
                                                                    remote_platform=remote_platform)
            serving_model_service.delete_serving_service(serving_model)
        # called times not increased
        mock_k8s_client.delete_config_map.assert_called_once()
        mock_k8s_client.delete_app.assert_called_once()
        mock_k8s_client.delete_service.assert_called_once()


if __name__ == '__main__':
    unittest.main()

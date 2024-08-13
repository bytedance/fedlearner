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

from google.protobuf.json_format import MessageToDict

from fedlearner_webconsole.mmgr.models import ModelJobGroup, Model, ModelType
from fedlearner_webconsole.proto import serving_pb2
from fedlearner_webconsole.serving.models import ServingModel, ServingModelStatus, ServingDeployment
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.db import db
from testing.no_web_server_test_case import NoWebServerTestCase


class ServingModelTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            model_job_group = ModelJobGroup()
            session.add(model_job_group)
            session.flush([model_job_group])

            model = Model()
            model.name = 'test_model_name_1'
            model.project_id = 1
            model.group_id = model_job_group.id
            session.add(model)
            session.flush([model])

            deployment = ServingDeployment()
            deployment.project_id = 1
            deploy_config = serving_pb2.RemoteDeployConfig(platform='test-platform',
                                                           payload='test-payload',
                                                           deploy_name='privacy-platform-test-serving',
                                                           model_src_path='')
            deployment.deploy_platform = json.dumps(MessageToDict(deploy_config))
            session.add(deployment)
            session.flush([deployment])

            serving_model = ServingModel()
            serving_model.project_id = 1
            serving_model.name = 'test-serving-model-1'
            serving_model.model_id = model.id
            serving_model.serving_deployment_id = deployment.id
            session.add(serving_model)
            session.commit()

            self.model_group_id = model_job_group.id
            self.model_id = model.id
            self.serving_model_id = serving_model.id

    def test_to_serving_service_detail(self):
        with db.session_scope() as session:
            serving_model: ServingModel = session.query(ServingModel).get(self.serving_model_id)
            expected_detail = serving_pb2.ServingServiceDetail(id=self.serving_model_id,
                                                               project_id=1,
                                                               name='test-serving-model-1',
                                                               model_id=self.model_id,
                                                               model_type=ModelType.NN_MODEL.name,
                                                               is_local=True,
                                                               status=ServingModelStatus.UNKNOWN.name,
                                                               support_inference=False)
            self.assertPartiallyEqual(to_dict(expected_detail),
                                      to_dict(serving_model.to_serving_service_detail()),
                                      ignore_fields=['created_at', 'updated_at', 'remote_platform'])
            self.assertEqual(0, serving_model.to_serving_service_detail().model_group_id)

            serving_model.model_group_id = self.serving_model_id
            expected_detail.model_group_id = self.model_group_id
            self.assertPartiallyEqual(to_dict(expected_detail),
                                      to_dict(serving_model.to_serving_service_detail()),
                                      ignore_fields=['created_at', 'updated_at', 'remote_platform'])

            expected_detail.remote_platform.CopyFrom(
                serving_pb2.ServingServiceRemotePlatform(
                    platform='test-platform',
                    payload='test-payload',
                ))
            self.assertPartiallyEqual(to_dict(expected_detail),
                                      to_dict(serving_model.to_serving_service_detail()),
                                      ignore_fields=['created_at', 'updated_at'])


if __name__ == '__main__':
    unittest.main()

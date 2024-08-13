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
from unittest.mock import patch, PropertyMock
from datetime import datetime
from google.protobuf.json_format import MessageToDict

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.workflow.models import WorkflowExternalState
from fedlearner_webconsole.mmgr.models import ModelJob, Model, ModelJobType, ModelJobGroup, ModelJobRole, \
    GroupCreateStatus, GroupAuthFrontendStatus, AlgorithmProjectList, ModelJobAuthFrontendStatus, \
    ModelJobCreateStatus, AuthStatus as ModelJobAuthStatus
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, JobDefinition
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobRef, ModelPb, ModelJobGroupRef, ModelJobGroupPb, \
    ModelJobGlobalConfig, ModelJobConfig
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus


class ModelTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            model = Model(id=1,
                          name='model',
                          uuid='uuid',
                          group_id=2,
                          project_id=3,
                          job_id=4,
                          model_job_id=5,
                          version=1,
                          created_at=datetime(2022, 5, 10, 0, 0, 0),
                          updated_at=datetime(2022, 5, 10, 0, 0, 0))
            session.add(model)
            session.commit()

    def test_to_proto(self):
        with db.session_scope() as session:
            model: Model = session.query(Model).get(1)
            pb = ModelPb(id=1,
                         name='model',
                         uuid='uuid',
                         group_id=2,
                         project_id=3,
                         algorithm_type='UNSPECIFIED',
                         job_id=4,
                         model_job_id=5,
                         version=1,
                         created_at=1652140800,
                         updated_at=1652140800)
            self.assertEqual(model.to_proto(), pb)
            model.algorithm_type = AlgorithmType.NN_VERTICAL
            pb.algorithm_type = 'NN_VERTICAL'
            self.assertEqual(model.to_proto(), pb)


class ModelJobTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='test-project')
            model_job = ModelJob(id=1,
                                 name='job',
                                 uuid='uuid',
                                 project_id=1,
                                 group_id=2,
                                 model_job_type=ModelJobType.TRAINING,
                                 role=ModelJobRole.COORDINATOR,
                                 algorithm_type=AlgorithmType.NN_VERTICAL,
                                 ticket_status=TicketStatus.PENDING,
                                 ticket_uuid='ticket_uuid',
                                 job_name='uuid-train-job',
                                 job_id=3,
                                 workflow_uuid='uuid',
                                 workflow_id=5,
                                 algorithm_id=6,
                                 dataset_id=7,
                                 creator_username='ada',
                                 coordinator_id=8,
                                 version=1,
                                 created_at=datetime(2022, 5, 10, 0, 0, 0),
                                 updated_at=datetime(2022, 5, 10, 0, 0, 0),
                                 metric_is_public=True,
                                 auto_update=True,
                                 auth_status=ModelJobAuthStatus.AUTHORIZED,
                                 error_message='error_message')
            session.add_all([project, model_job])
            session.commit()

    @patch('fedlearner_webconsole.project.models.Project.get_storage_root_path')
    def test_exported_model_path(self, mock_get_storage_root_path):
        mock_get_storage_root_path.return_value = '/data/'
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            session.add(model_job)
            session.flush()
            # test for model_job.get_exported_model_path
            expected_path = f'/data/job_output/{model_job.job_name}/exported_models'
            self.assertEqual(model_job.get_exported_model_path(), expected_path)
            # test for model.get_exported_model_path
            model_path = '/data/model_output/uuid'
            model = Model(model_path=model_path)
            expected_path = '/data/model_output/uuid/exported_models'
            self.assertEqual(model.get_exported_model_path(), expected_path)

    @patch('fedlearner_webconsole.mmgr.models.ModelJob.state', new_callable=PropertyMock)
    def test_is_deletable(self, mock_state):
        mock_state.return_value = WorkflowExternalState.RUNNING
        model_job = ModelJob(name='model_job')
        self.assertEqual(model_job.is_deletable(), False)
        mock_state.return_value = WorkflowExternalState.FAILED
        self.assertEqual(model_job.is_deletable(), True)

    def test_to_ref(self):
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).get(1)
            ref = ModelJobRef(id=1,
                              name='job',
                              uuid='uuid',
                              project_id=1,
                              group_id=2,
                              model_job_type='TRAINING',
                              role='COORDINATOR',
                              algorithm_type='NN_VERTICAL',
                              algorithm_id=6,
                              state='PENDING_ACCEPT',
                              configured=False,
                              creator_username='ada',
                              coordinator_id=8,
                              version=1,
                              created_at=1652140800,
                              updated_at=1652140800,
                              metric_is_public=True,
                              status='PENDING',
                              auth_frontend_status='TICKET_PENDING',
                              auth_status='AUTHORIZED',
                              auto_update=True,
                              participants_info=ParticipantsInfo())
            self.assertEqual(model_job.to_ref(), ref)

    def test_to_proto(self):
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).get(1)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid',
                                                 global_config={'test': ModelJobConfig(algorithm_uuid='uuid')})
            model_job.set_global_config(global_config)
            self.assertPartiallyEqual(MessageToDict(model_job.to_proto()), {
                'id': '1',
                'name': 'job',
                'uuid': 'uuid',
                'role': 'COORDINATOR',
                'modelJobType': 'TRAINING',
                'algorithmType': 'NN_VERTICAL',
                'algorithmId': '6',
                'groupId': '2',
                'projectId': '1',
                'state': 'PENDING_ACCEPT',
                'jobId': '3',
                'workflowId': '5',
                'datasetId': '7',
                'creatorUsername': 'ada',
                'coordinatorId': '8',
                'version': '1',
                'jobName': 'uuid-train-job',
                'metricIsPublic': True,
                'status': 'PENDING',
                'authStatus': 'AUTHORIZED',
                'autoUpdate': True,
                'errorMessage': 'error_message',
                'globalConfig': {
                    'globalConfig': {
                        'test': {
                            'algorithmUuid': 'uuid'
                        }
                    },
                    'datasetUuid': 'uuid'
                },
                'authFrontendStatus': 'TICKET_PENDING',
                'participantsInfo': {},
            },
                                      ignore_fields=['createdAt', 'updatedAt'])

    def test_set_and_get_global_config(self):
        global_config = ModelJobGlobalConfig(dataset_uuid='uuid',
                                             global_config={'test': ModelJobConfig(algorithm_uuid='uuid')})
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).get(1)
            self.assertIsNone(model_job.get_global_config())
            model_job.set_global_config(proto=global_config)
            session.commit()
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).get(1)
            self.assertEqual(model_job.get_global_config(), global_config)

    def test_get_model_job_auth_frontend_status(self):
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            # case 1
            self.assertEqual(model_job.get_model_job_auth_frontend_status(), ModelJobAuthFrontendStatus.TICKET_PENDING)
            # case 2
            model_job.ticket_status = TicketStatus.DECLINED
            self.assertEqual(model_job.get_model_job_auth_frontend_status(), ModelJobAuthFrontendStatus.TICKET_DECLINED)
            # case 3
            model_job.ticket_status = TicketStatus.APPROVED
            model_job.auth_status = ModelJobAuthStatus.PENDING
            self.assertEqual(model_job.get_model_job_auth_frontend_status(),
                             ModelJobAuthFrontendStatus.SELF_AUTH_PENDING)
            # case 4
            model_job.auth_status = ModelJobAuthStatus.AUTHORIZED
            participants_info = ParticipantsInfo(
                participants_map={
                    'test_1': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                    'test_2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                })
            model_job.set_participants_info(participants_info)
            model_job.create_status = ModelJobCreateStatus.PENDING
            self.assertEqual(model_job.get_model_job_auth_frontend_status(), ModelJobAuthFrontendStatus.CREATE_PENDING)
            # case 5
            model_job.create_status = ModelJobCreateStatus.FAILED
            self.assertEqual(model_job.get_model_job_auth_frontend_status(), ModelJobAuthFrontendStatus.CREATE_FAILED)
            # case 6
            model_job.create_status = ModelJobCreateStatus.SUCCEEDED
            self.assertEqual(model_job.get_model_job_auth_frontend_status(),
                             ModelJobAuthFrontendStatus.PART_AUTH_PENDING)
            # case 7
            participants_info = ParticipantsInfo(
                participants_map={
                    'test_1': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'test_2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                })
            model_job.set_participants_info(participants_info)
            self.assertEqual(model_job.get_model_job_auth_frontend_status(), ModelJobAuthFrontendStatus.ALL_AUTHORIZED)
            # case 8
            model_job.ticket_uuid = None
            model_job.ticket_status = TicketStatus.PENDING
            self.assertEqual(model_job.get_model_job_auth_frontend_status(), ModelJobAuthFrontendStatus.ALL_AUTHORIZED)
            self.assertEqual(model_job.ticket_status, TicketStatus.APPROVED)


class ModelJobGroupTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            config = WorkflowDefinition(job_definitions=[
                JobDefinition(name='train-job',
                              job_type=JobDefinition.JobType.TREE_MODEL_TRAINING,
                              variables=[Variable(name='mode', value='train')])
            ])
            job = ModelJob(id=1,
                           name='job',
                           uuid='uuid',
                           project_id=2,
                           group_id=1,
                           model_job_type=ModelJobType.TRAINING,
                           algorithm_type=AlgorithmType.NN_VERTICAL,
                           auth_status=ModelJobAuthStatus.AUTHORIZED,
                           auto_update=True,
                           created_at=datetime(2022, 5, 10, 0, 0, 0),
                           updated_at=datetime(2022, 5, 10, 0, 0, 0),
                           version=1)
            group = ModelJobGroup(id=1,
                                  name='group',
                                  uuid='uuid',
                                  project_id=2,
                                  role=ModelJobRole.COORDINATOR,
                                  authorized=False,
                                  ticket_status=TicketStatus.PENDING,
                                  ticket_uuid='ticket_uuid',
                                  dataset_id=3,
                                  algorithm_type=AlgorithmType.NN_VERTICAL,
                                  algorithm_project_id=4,
                                  algorithm_id=5,
                                  creator_username='ada',
                                  coordinator_id=6,
                                  created_at=datetime(2022, 5, 10, 0, 0, 0),
                                  updated_at=datetime(2022, 5, 10, 0, 0, 0))
            algorithm_project_list = AlgorithmProjectList()
            algorithm_project_list.algorithm_projects['test'] = 'uuid-test'
            algorithm_project_list.algorithm_projects['peer'] = 'uuid-peer'
            group.set_algorithm_project_uuid_list(algorithm_project_list)
            group.set_config(config)
            session.add_all([job, group])
            session.commit()

    def test_get_config(self):
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            self.assertEqual(
                group.get_config(),
                WorkflowDefinition(job_definitions=[
                    JobDefinition(name='train-job',
                                  job_type=JobDefinition.JobType.TREE_MODEL_TRAINING,
                                  variables=[Variable(name='mode', value='train')])
                ]))

    @patch('fedlearner_webconsole.mmgr.models.ModelJob.state', new_callable=PropertyMock)
    def test_is_deletable(self, mock_state):
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).get(1)
            mock_state.return_value = WorkflowExternalState.RUNNING
            self.assertEqual(group.is_deletable(), False)
            mock_state.return_value = WorkflowExternalState.STOPPED
            self.assertEqual(group.is_deletable(), True)

    def test_auth_status(self):
        group = ModelJobGroup(id=2, auth_status=None)
        self.assertEqual(group.auth_status, AuthStatus.PENDING)
        group.authorized = True
        self.assertEqual(group.auth_status, AuthStatus.AUTHORIZED)
        group.authorized = False
        group.auth_status = AuthStatus.AUTHORIZED
        self.assertEqual(group.auth_status, AuthStatus.AUTHORIZED)
        with db.session_scope() as session:
            session.add(group)
            session.commit()
            self.assertEqual(group._auth_status, AuthStatus.AUTHORIZED)  # pylint: disable=protected-access

    def test_get_group_auth_frontend_status(self):
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            # case 1
            self.assertEqual(group.get_group_auth_frontend_status(), GroupAuthFrontendStatus.TICKET_PENDING)
            # case 2
            group.ticket_status = TicketStatus.DECLINED
            self.assertEqual(group.get_group_auth_frontend_status(), GroupAuthFrontendStatus.TICKET_DECLINED)
            # case 3
            group.ticket_status = TicketStatus.APPROVED
            group.authorized = False
            self.assertEqual(group.get_group_auth_frontend_status(), GroupAuthFrontendStatus.SELF_AUTH_PENDING)
            # case 4
            group.authorized = True
            participants_info = ParticipantsInfo(
                participants_map={
                    'test_1': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                    'test_2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                })
            group.set_participants_info(participants_info)
            group.status = GroupCreateStatus.PENDING
            self.assertEqual(group.get_group_auth_frontend_status(), GroupAuthFrontendStatus.CREATE_PENDING)
            # case 5
            group.status = GroupCreateStatus.FAILED
            self.assertEqual(group.get_group_auth_frontend_status(), GroupAuthFrontendStatus.CREATE_FAILED)
            # case 6
            group.status = GroupCreateStatus.SUCCEEDED
            self.assertEqual(group.get_group_auth_frontend_status(), GroupAuthFrontendStatus.PART_AUTH_PENDING)
            # case 7
            participants_info = ParticipantsInfo(
                participants_map={
                    'test_1': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'test_2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                })
            group.set_participants_info(participants_info)
            self.assertEqual(group.get_group_auth_frontend_status(), GroupAuthFrontendStatus.ALL_AUTHORIZED)
            # case 8
            group.ticket_uuid = None
            group.ticket_status = TicketStatus.PENDING
            self.assertEqual(group.get_group_auth_frontend_status(), GroupAuthFrontendStatus.ALL_AUTHORIZED)
            self.assertEqual(group.ticket_status, TicketStatus.APPROVED)

    def test_to_ref(self):
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).get(1)
            ref = ModelJobGroupRef(id=1,
                                   name='group',
                                   uuid='uuid',
                                   role='COORDINATOR',
                                   project_id=2,
                                   algorithm_type='NN_VERTICAL',
                                   configured=True,
                                   creator_username='ada',
                                   coordinator_id=6,
                                   latest_job_state='PENDING',
                                   auth_frontend_status='TICKET_PENDING',
                                   auth_status='PENDING',
                                   participants_info=group.get_participants_info(),
                                   created_at=1652140800,
                                   updated_at=1652140800)
            self.assertEqual(group.to_ref(), ref)

    def test_to_proto(self):
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).get(1)
            proto = ModelJobGroupPb(id=1,
                                    name='group',
                                    uuid='uuid',
                                    role='COORDINATOR',
                                    project_id=2,
                                    dataset_id=3,
                                    algorithm_type='NN_VERTICAL',
                                    algorithm_project_id=4,
                                    algorithm_id=5,
                                    configured=True,
                                    creator_username='ada',
                                    coordinator_id=6,
                                    latest_job_state='PENDING',
                                    auth_frontend_status='TICKET_PENDING',
                                    auth_status='PENDING',
                                    auto_update_status='INITIAL',
                                    participants_info=group.get_participants_info(),
                                    algorithm_project_uuid_list=group.get_algorithm_project_uuid_list(),
                                    created_at=1652140800,
                                    updated_at=1652140800)
            config = WorkflowDefinition(job_definitions=[
                JobDefinition(name='train-job',
                              job_type=JobDefinition.JobType.TREE_MODEL_TRAINING,
                              variables=[Variable(name='mode', value='train')])
            ])
            proto.config.MergeFrom(config)
            proto.model_jobs.append(
                ModelJobRef(id=1,
                            name='job',
                            uuid='uuid',
                            group_id=1,
                            project_id=2,
                            role='PARTICIPANT',
                            model_job_type='TRAINING',
                            algorithm_type='NN_VERTICAL',
                            state='PENDING_ACCEPT',
                            created_at=1652140800,
                            updated_at=1652140800,
                            version=1,
                            status='PENDING',
                            auto_update=True,
                            auth_status='AUTHORIZED',
                            auth_frontend_status='ALL_AUTHORIZED',
                            participants_info=ParticipantsInfo()))
            self.assertEqual(group.to_proto(), proto)


if __name__ == '__main__':
    unittest.main()

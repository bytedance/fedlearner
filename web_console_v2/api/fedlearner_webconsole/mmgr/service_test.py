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

import grpc
import unittest
from unittest.mock import patch, Mock
from google.protobuf.struct_pb2 import Value
from google.protobuf.empty_pb2 import Empty

from testing.common import NoWebServerTestCase
from testing.rpc.client import FakeRpcError
from fedlearner_webconsole.db import db
from fedlearner_webconsole.initial_db import _insert_or_update_templates
from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.mmgr.models import ModelJob, ModelJobGroup, ModelJobType, Model, ModelJobRole, \
    ModelJobStatus, AuthStatus
from fedlearner_webconsole.mmgr.service import ModelJobService, ModelJobGroupService, ModelService
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.algorithm.models import AlgorithmType, Algorithm, AlgorithmProject
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobState, DatasetJobKind, DatasetType, \
    DataBatch, DatasetJobStage
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobGlobalConfig, ModelJobConfig, AlgorithmProjectList
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, ModelTrainingCronJobInput
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo


class ModelJobServiceTest(NoWebServerTestCase):

    def setUp(self) -> None:

        super().setUp()
        with db.session_scope() as session:
            _insert_or_update_templates(session)
            dataset_job = DatasetJob(id=1,
                                     name='datasetjob',
                                     uuid='uuid',
                                     state=DatasetJobState.SUCCEEDED,
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     kind=DatasetJobKind.OT_PSI_DATA_JOIN)
            dataset = Dataset(id=2,
                              uuid='uuid',
                              name='datasetjob',
                              dataset_type=DatasetType.PSI,
                              path='/data/dataset/haha')
            dataset_rsa = Dataset(id=3,
                                  uuid='uuid_rsa',
                                  name='dataset_rsa',
                                  dataset_type=DatasetType.PSI,
                                  path='/data/dataset/haha')
            dataset_job_rsa = DatasetJob(id=2,
                                         name='dataset_job_rsa',
                                         uuid='uuid_rsa',
                                         state=DatasetJobState.SUCCEEDED,
                                         project_id=1,
                                         input_dataset_id=1,
                                         output_dataset_id=3,
                                         kind=DatasetJobKind.RSA_PSI_DATA_JOIN)
            dataset_job_stage = DatasetJobStage(id=1,
                                                uuid='uuid',
                                                name='dataset_job_stage_1',
                                                project_id=1,
                                                dataset_job_id=1,
                                                data_batch_id=1,
                                                state=DatasetJobState.SUCCEEDED)
            data_batch = DataBatch(id=1,
                                   name='data_batch_1',
                                   dataset_id=dataset.id,
                                   latest_parent_dataset_job_stage_id=1)
            model_job = ModelJob(name='test-model-job',
                                 model_job_type=ModelJobType.TRAINING,
                                 algorithm_type=AlgorithmType.TREE_VERTICAL,
                                 dataset_id=2,
                                 model_id=1,
                                 project_id=1,
                                 workflow_uuid='test-uuid')
            algorithm = Algorithm(id=1, name='algo', uuid='uuid', project_id=1)
            project = Project(id=1, name='project')
            model_job_group = ModelJobGroup(id=1, name='model_job_group', uuid='uuid')
            participant1 = Participant(id=1, name='demo1', domain_name='fl-demo1.com')
            participant2 = Participant(id=2, name='demo2', domain_name='fl-demo2.com')
            project_part1 = ProjectParticipant(id=1, project_id=1, participant_id=1)
            project_part2 = ProjectParticipant(id=2, project_id=1, participant_id=2)
            session.add_all([
                model_job, dataset, dataset_job, algorithm, project, participant1, participant2, project_part1,
                project_part2, model_job_group, dataset_rsa, dataset_job_rsa, dataset_job_stage, data_batch
            ])
            session.commit()

    @staticmethod
    def _get_workflow_config():
        return WorkflowDefinition(job_definitions=[
            JobDefinition(name='train-job',
                          job_type=JobDefinition.JobType.TREE_MODEL_TRAINING,
                          variables=[
                              Variable(name='mode', value='train'),
                              Variable(name='data_source'),
                              Variable(name='data_path'),
                              Variable(name='file_wildcard'),
                          ],
                          yaml_template='{}')
        ])

    def test_config_model_job_create_workflow(self):
        config = self._get_workflow_config()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            ModelJobService(session).config_model_job(model_job,
                                                      config=config,
                                                      create_workflow=True,
                                                      workflow_uuid='test-uuid')
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            workflow = session.query(Workflow).filter_by(uuid='test-uuid').first()
            self.assertEqual(workflow.creator, 's_y_s_t_e_m')
            self.assertEqual(model_job.job_name, 'test-uuid-train-job')
            self.assertEqual(model_job.job_id, workflow.owned_jobs[0].id)
            self.assertEqual(model_job.workflow.template.name, 'sys-preset-tree-model')
            self.assertEqual(
                model_job.workflow.get_config(),
                WorkflowDefinition(job_definitions=[
                    JobDefinition(name='train-job',
                                  job_type=JobDefinition.JobType.TREE_MODEL_TRAINING,
                                  variables=[
                                      Variable(name='mode', value='train'),
                                      Variable(name='data_source',
                                               value='',
                                               value_type=Variable.ValueType.STRING,
                                               typed_value=Value(string_value='')),
                                      Variable(name='data_path',
                                               value='/data/dataset/haha/batch',
                                               value_type=Variable.ValueType.STRING,
                                               typed_value=Value(string_value='/data/dataset/haha/batch')),
                                      Variable(name='file_wildcard',
                                               value='**/part*',
                                               value_type=Variable.ValueType.STRING,
                                               typed_value=Value(string_value='**/part*')),
                                  ],
                                  yaml_template='{}')
                ]))

    def test_config_model_job_not_create_workflow(self):
        config = self._get_workflow_config()
        with db.session_scope() as session:
            workflow = Workflow(name='test-workflow', uuid='test-uuid', state=WorkflowState.NEW, project_id=1)
            session.add(workflow)
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            ModelJobService(session).config_model_job(model_job,
                                                      config=config,
                                                      create_workflow=False,
                                                      workflow_uuid='test-uuid')
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            workflow = session.query(Workflow).filter_by(name='test-workflow').first()
            self.assertEqual(workflow.creator, 's_y_s_t_e_m')
            self.assertEqual(model_job.job_name, 'test-uuid-train-job')
            self.assertEqual(model_job.job_id, workflow.owned_jobs[0].id)
            self.assertEqual(model_job.workflow.template.name, 'sys-preset-tree-model')
            self.assertEqual(
                model_job.workflow.get_config(),
                WorkflowDefinition(job_definitions=[
                    JobDefinition(name='train-job',
                                  job_type=JobDefinition.JobType.TREE_MODEL_TRAINING,
                                  variables=[
                                      Variable(name='mode', value='train'),
                                      Variable(name='data_source',
                                               value='',
                                               value_type=Variable.ValueType.STRING,
                                               typed_value=Value(string_value='')),
                                      Variable(name='data_path',
                                               value='/data/dataset/haha/batch',
                                               value_type=Variable.ValueType.STRING,
                                               typed_value=Value(string_value='/data/dataset/haha/batch')),
                                      Variable(name='file_wildcard',
                                               value='**/part*',
                                               value_type=Variable.ValueType.STRING,
                                               typed_value=Value(string_value='**/part*')),
                                  ],
                                  yaml_template='{}')
                ]))

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.create_model_job')
    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    def test_create_model_job(self, mock_get_system_info, mock_create_model_job):
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='test')
        # fail due to dataset uuid is None
        with db.session_scope() as session:
            service = ModelJobService(session=session)
            global_config = ModelJobGlobalConfig()
            with self.assertRaises(AssertionError, msg='dataset uuid must not be None'):
                service.create_model_job(name='name',
                                         uuid='uuid',
                                         group_id=1,
                                         project_id=1,
                                         role=ModelJobRole.COORDINATOR,
                                         model_job_type=ModelJobType.TRAINING,
                                         algorithm_type=AlgorithmType.NN_VERTICAL,
                                         global_config=global_config)
        # fail due to dataset is not found
        with db.session_scope() as session:
            service = ModelJobService(session=session)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid1')
            with self.assertRaises(AssertionError, msg='dataset with uuid uuid1 is not found'):
                service.create_model_job(name='name',
                                         uuid='uuid',
                                         group_id=1,
                                         project_id=1,
                                         role=ModelJobRole.COORDINATOR,
                                         model_job_type=ModelJobType.TRAINING,
                                         algorithm_type=AlgorithmType.NN_VERTICAL,
                                         global_config=global_config)
        # fail due to domain name in model_job_config is None
        with db.session_scope() as session:
            service = ModelJobService(session=session)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid')
            with self.assertRaises(AssertionError, msg='model_job_config of self domain name test must not be None'):
                service.create_model_job(name='name',
                                         uuid='uuid',
                                         group_id=1,
                                         project_id=1,
                                         role=ModelJobRole.COORDINATOR,
                                         model_job_type=ModelJobType.TRAINING,
                                         algorithm_type=AlgorithmType.NN_VERTICAL,
                                         global_config=global_config)
        # create model job when role is participant and model_job_type is TRAINING
        with db.session_scope() as session:
            service = ModelJobService(session=session)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid',
                                                 global_config={'test': ModelJobConfig(algorithm_uuid='uuid')})
            service.create_model_job(name='model_job_1',
                                     uuid='uuid-1',
                                     group_id=2,
                                     project_id=3,
                                     coordinator_id=1,
                                     role=ModelJobRole.PARTICIPANT,
                                     model_job_type=ModelJobType.TRAINING,
                                     algorithm_type=AlgorithmType.NN_VERTICAL,
                                     global_config=global_config,
                                     version=3)
            session.commit()
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).filter_by(name='model_job_1').first()
            self.assertEqual(model_job.model_job_type, ModelJobType.TRAINING)
            self.assertEqual(model_job.algorithm_type, AlgorithmType.NN_VERTICAL)
            self.assertEqual(model_job.dataset_id, 2)
            self.assertEqual(model_job.get_global_config(), global_config)
            self.assertEqual(model_job.algorithm_id, 1)
            self.assertEqual(model_job.version, 3)
            self.assertEqual(model_job.group_id, 2)
            self.assertEqual(model_job.project_id, 3)
            self.assertEqual(model_job.coordinator_id, 1)
            self.assertEqual(model_job.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(
                model_job.get_participants_info(),
                ParticipantsInfo(participants_map={'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)}))
            self.assertEqual(model_job.status, ModelJobStatus.PENDING)
            self.assertEqual(model_job.auto_update, False)
        # create model job when role is coordinator and model_job_type is EVALUATION
        with db.session_scope() as session:
            service = ModelJobService(session)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid',
                                                 global_config={
                                                     'test': ModelJobConfig(algorithm_uuid='uuid'),
                                                     'demo1': ModelJobConfig(algorithm_uuid='uuid'),
                                                     'demo2': ModelJobConfig(algorithm_uuid='uuid')
                                                 })
            mock_create_model_job.side_effect = [Empty(), Empty()]
            service.create_model_job(name='model_job_2',
                                     uuid='uuid-2',
                                     group_id=1,
                                     project_id=1,
                                     role=ModelJobRole.COORDINATOR,
                                     model_job_type=ModelJobType.EVALUATION,
                                     algorithm_type=AlgorithmType.NN_VERTICAL,
                                     global_config=global_config,
                                     version=3)
            session.commit()
        mock_create_model_job.assert_called()
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).filter_by(name='model_job_2').first()
            self.assertEqual(model_job.model_job_type, ModelJobType.EVALUATION)
            self.assertEqual(model_job.algorithm_type, AlgorithmType.NN_VERTICAL)
            self.assertEqual(model_job.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(
                model_job.get_participants_info(),
                ParticipantsInfo(
                    participants_map={
                        'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                        'demo1': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                        'demo2': ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                    }))
            self.assertEqual(model_job.status, ModelJobStatus.PENDING)
            self.assertEqual(model_job.coordinator_id, 0)
            self.assertEqual(model_job.auto_update, False)
        # create model job when role is participant and model_job_type is EVALUATION
        mock_create_model_job.reset_mock()
        with db.session_scope() as session:
            service = ModelJobService(session)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid',
                                                 global_config={
                                                     'test': ModelJobConfig(algorithm_uuid='uuid'),
                                                     'demo1': ModelJobConfig(algorithm_uuid='uuid'),
                                                     'demo2': ModelJobConfig(algorithm_uuid='uuid')
                                                 })
            mock_create_model_job.side_effect = [Empty(), Empty()]
            service.create_model_job(name='model_job_5',
                                     uuid='uuid-5',
                                     group_id=1,
                                     project_id=1,
                                     role=ModelJobRole.PARTICIPANT,
                                     model_job_type=ModelJobType.EVALUATION,
                                     algorithm_type=AlgorithmType.NN_VERTICAL,
                                     global_config=global_config,
                                     version=3)
            session.commit()
        mock_create_model_job.assert_not_called()
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).filter_by(name='model_job_5').first()
            self.assertEqual(model_job.auth_status, AuthStatus.PENDING)
            self.assertEqual(
                model_job.get_participants_info(),
                ParticipantsInfo(
                    participants_map={
                        'test': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                        'demo1': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                        'demo2': ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                    }))
        # create eval horizontal model job when role is coordinator
        mock_create_model_job.reset_mock()
        with db.session_scope() as session:
            service = ModelJobService(session)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid',
                                                 global_config={
                                                     'test': ModelJobConfig(algorithm_uuid='uuid'),
                                                     'demo1': ModelJobConfig(algorithm_uuid='uuid'),
                                                     'demo2': ModelJobConfig(algorithm_uuid='uuid')
                                                 })
            service.create_model_job(name='model_job_3',
                                     uuid='uuid-3',
                                     project_id=1,
                                     group_id=None,
                                     role=ModelJobRole.COORDINATOR,
                                     model_job_type=ModelJobType.EVALUATION,
                                     algorithm_type=AlgorithmType.NN_HORIZONTAL,
                                     global_config=global_config,
                                     version=4)
            session.commit()
        mock_create_model_job.assert_not_called()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='model_job_3').first()
            self.assertEqual(model_job.model_job_type, ModelJobType.EVALUATION)
            self.assertEqual(model_job.algorithm_type, AlgorithmType.NN_HORIZONTAL)
            self.assertEqual(model_job.auth_status, AuthStatus.AUTHORIZED)
        # create predict horizontal model job when role is coordinator
        mock_create_model_job.reset_mock()
        with db.session_scope() as session:
            service = ModelJobService(session)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid',
                                                 global_config={
                                                     'test': ModelJobConfig(algorithm_uuid='uuid'),
                                                     'demo1': ModelJobConfig(algorithm_uuid='uuid'),
                                                     'demo2': ModelJobConfig(algorithm_uuid='uuid')
                                                 })
            service.create_model_job(name='model_job_4',
                                     uuid='uuid-4',
                                     project_id=1,
                                     group_id=None,
                                     role=ModelJobRole.COORDINATOR,
                                     model_job_type=ModelJobType.PREDICTION,
                                     algorithm_type=AlgorithmType.NN_HORIZONTAL,
                                     global_config=global_config,
                                     version=4)
            session.commit()
        mock_create_model_job.assert_not_called()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='model_job_4').first()
            self.assertEqual(model_job.model_job_type, ModelJobType.PREDICTION)
            self.assertEqual(model_job.algorithm_type, AlgorithmType.NN_HORIZONTAL)
            self.assertEqual(model_job.auth_status, AuthStatus.AUTHORIZED)
        # fail due to grpc error
        with db.session_scope() as session:
            service = ModelJobService(session)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid',
                                                 global_config={
                                                     'test': ModelJobConfig(algorithm_uuid='uuid'),
                                                     'demo1': ModelJobConfig(algorithm_uuid='uuid'),
                                                     'demo2': ModelJobConfig(algorithm_uuid='uuid')
                                                 })
            mock_create_model_job.side_effect = [
                Empty(), FakeRpcError(grpc.StatusCode.UNIMPLEMENTED, 'rpc not implemented')
            ]
            with self.assertRaises(Exception):
                service.create_model_job(name='model_job_2',
                                         uuid='uuid-2',
                                         group_id=1,
                                         project_id=1,
                                         role=ModelJobRole.COORDINATOR,
                                         model_job_type=ModelJobType.TRAINING,
                                         algorithm_type=AlgorithmType.NN_VERTICAL,
                                         global_config=global_config,
                                         version=3)

    def test_update_model_job_status(self):
        with db.session_scope() as session:
            workflow = Workflow(id=1, uuid='test-uuid', state=WorkflowState.NEW)
            session.add(workflow)
            session.commit()
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            ModelJobService(session).update_model_job_status(model_job)
            self.assertEqual(model_job.status, ModelJobStatus.PENDING)
            workflow = session.query(Workflow).filter_by(uuid='test-uuid').first()
            workflow.state = WorkflowState.RUNNING
            ModelJobService(session).update_model_job_status(model_job)
            self.assertEqual(model_job.status, ModelJobStatus.RUNNING)
            workflow.state = WorkflowState.STOPPED
            ModelJobService(session).update_model_job_status(model_job)
            self.assertEqual(model_job.status, ModelJobStatus.STOPPED)
            workflow.state = WorkflowState.COMPLETED
            ModelJobService(session).update_model_job_status(model_job)
            self.assertEqual(model_job.status, ModelJobStatus.SUCCEEDED)
            workflow.state = WorkflowState.FAILED
            ModelJobService(session).update_model_job_status(model_job)
            self.assertEqual(model_job.status, ModelJobStatus.FAILED)

    @patch('fedlearner_webconsole.project.services.SettingService.get_system_info')
    def test_initialize_auth_status(self, mock_system_info):
        mock_system_info.return_value = SystemInfo(pure_domain_name='test', name='name')
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            ModelJobService(session).initialize_auth_status(model_job)
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            self.assertEqual(model_job.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(
                model_job.get_participants_info(),
                ParticipantsInfo(
                    participants_map={
                        'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                        'demo1': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                        'demo2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                    }))
        mock_system_info.return_value = SystemInfo(pure_domain_name='test', name='name')
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            model_job.algorithm_type = AlgorithmType.NN_HORIZONTAL
            ModelJobService(session).initialize_auth_status(model_job)
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            self.assertEqual(model_job.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(
                model_job.get_participants_info(),
                ParticipantsInfo(
                    participants_map={
                        'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                        'demo1': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                        'demo2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                    }))
        mock_system_info.return_value = SystemInfo(pure_domain_name='test', name='name')
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            model_job.algorithm_type = AlgorithmType.TREE_VERTICAL
            model_job.model_job_type = ModelJobType.EVALUATION
            ModelJobService(session).initialize_auth_status(model_job)
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            self.assertEqual(model_job.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(
                model_job.get_participants_info(),
                ParticipantsInfo(
                    participants_map={
                        'test': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                        'demo1': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                        'demo2': ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                    }))
        mock_system_info.return_value = SystemInfo(pure_domain_name='test', name='name')
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            model_job.role = ModelJobRole.COORDINATOR
            ModelJobService(session).initialize_auth_status(model_job)
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            self.assertEqual(model_job.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(
                model_job.get_participants_info(),
                ParticipantsInfo(
                    participants_map={
                        'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                        'demo1': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                        'demo2': ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                    }))

    @patch('fedlearner_webconsole.project.services.SettingService.get_system_info')
    def test_update_model_job_auth_status(self, mock_get_system_info):
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='test')
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            ModelJobService.update_model_job_auth_status(model_job, AuthStatus.AUTHORIZED)
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            self.assertEqual(model_job.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(
                model_job.get_participants_info(),
                ParticipantsInfo(participants_map={'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)}))
            ModelJobService.update_model_job_auth_status(model_job, AuthStatus.PENDING)
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='test-model-job').first()
            self.assertEqual(model_job.auth_status, AuthStatus.PENDING)
            self.assertEqual(
                model_job.get_participants_info(),
                ParticipantsInfo(participants_map={'test': ParticipantInfo(auth_status=AuthStatus.PENDING.name)}))

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.create_model_job')
    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    def test_create_auto_update_model_job(self, mock_get_system_info, mock_create_model_job):
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='test')
        # fail due to algorithm type not supported
        with db.session_scope() as session:
            service = ModelJobService(session=session)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid')
            with self.assertRaises(AssertionError, msg='auto update is only supported for nn vertical train'):
                service.create_model_job(name='name',
                                         uuid='uuid',
                                         group_id=1,
                                         project_id=1,
                                         role=ModelJobRole.COORDINATOR,
                                         model_job_type=ModelJobType.TRAINING,
                                         algorithm_type=AlgorithmType.NN_HORIZONTAL,
                                         global_config=global_config,
                                         data_batch_id=1)
        # fail due to dataset job type not supported
        with db.session_scope() as session:
            service = ModelJobService(session=session)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid_rsa')
            with self.assertRaises(AssertionError, msg='auto update is not supported for RSA-PSI dataset'):
                service.create_model_job(name='name',
                                         uuid='uuid',
                                         group_id=1,
                                         project_id=1,
                                         role=ModelJobRole.COORDINATOR,
                                         model_job_type=ModelJobType.TRAINING,
                                         algorithm_type=AlgorithmType.NN_VERTICAL,
                                         global_config=global_config,
                                         data_batch_id=1)
        # fail due to data batch is not found
        with db.session_scope() as session:
            service = ModelJobService(session=session)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid')
            with self.assertRaises(AssertionError, msg='data batch 2 is not found'):
                service.create_model_job(name='name',
                                         uuid='uuid',
                                         group_id=1,
                                         project_id=1,
                                         role=ModelJobRole.COORDINATOR,
                                         model_job_type=ModelJobType.TRAINING,
                                         algorithm_type=AlgorithmType.NN_VERTICAL,
                                         global_config=global_config,
                                         data_batch_id=2)
        # create success
        with db.session_scope() as session:
            service = ModelJobService(session=session)
            global_config = ModelJobGlobalConfig(dataset_uuid='uuid',
                                                 global_config={'test': ModelJobConfig(algorithm_uuid='uuid')})
            service.create_model_job(name='model_job_1',
                                     uuid='uuid',
                                     group_id=1,
                                     project_id=1,
                                     role=ModelJobRole.COORDINATOR,
                                     model_job_type=ModelJobType.TRAINING,
                                     algorithm_type=AlgorithmType.NN_VERTICAL,
                                     global_config=global_config,
                                     data_batch_id=1)
            session.commit()
        mock_create_model_job.assert_called()
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).filter_by(name='model_job_1').first()
            self.assertEqual(model_job.data_batch_id, 1)
            self.assertEqual(model_job.auto_update, True)
            global_config.dataset_job_stage_uuid = 'uuid'
            self.assertEqual(model_job.get_global_config(), global_config)


class ModelServiceTest(NoWebServerTestCase):

    _MODEL_NAME = 'test-model'
    _PROJECT_ID = 123
    _GROUP_ID = 123
    _MODEL_JOB_ID = 123
    _JOB_ID = 123

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=self._PROJECT_ID, name='test-project')
            session.add(project)
            session.flush()
            workflow = Workflow(name='test-workflow', project_id=project.id)
            session.add(workflow)
            session.flush()
            workflow = Workflow(id=1, name='workflow', uuid='uuid', project_id=project.id)
            job = Job(id=self._JOB_ID,
                      name='uuid-nn-model',
                      project_id=project.id,
                      job_type=JobType.NN_MODEL_TRANINING,
                      state=JobState.COMPLETED,
                      workflow_id=workflow.id)
            job.set_config(JobDefinition(name='nn-model'))
            session.add(job)
            group = ModelJobGroup(id=self._GROUP_ID, name='test-group', project_id=project.id)
            session.add(group)
            session.flush()
            model_job = ModelJob(id=self._MODEL_JOB_ID,
                                 name='test-model-job',
                                 uuid='test-uuid',
                                 algorithm_type=AlgorithmType.NN_VERTICAL,
                                 model_job_type=ModelJobType.NN_TRAINING,
                                 group_id=group.id,
                                 project_id=project.id,
                                 job_name=job.name,
                                 job_id=job.id,
                                 version=2)
            session.add(model_job)
            session.commit()

    @patch('fedlearner_webconsole.project.models.Project.get_storage_root_path')
    def test_create_model_from_model_job(self, mock_get_storage_root_path):
        mock_get_storage_root_path.return_value = '/data'
        with db.session_scope() as session:
            service = ModelService(session)
            job = session.query(Job).get(self._JOB_ID)
            model_job = session.query(ModelJob).get(self._MODEL_JOB_ID)
            service.create_model_from_model_job(model_job=model_job)
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(self._MODEL_JOB_ID)
            model: Model = session.query(Model).filter_by(uuid=model_job.uuid).first()
            self.assertEqual(model.name, 'test-group-v2')
            self.assertEqual(model.job_id, job.id)
            self.assertEqual(model.project_id, self._PROJECT_ID)
            self.assertEqual(model.model_path, '/data/job_output/uuid-nn-model')
            self.assertEqual(model.model_job_id, model_job.id)
            self.assertEqual(model.group_id, model_job.group_id)

        mock_get_storage_root_path.return_value = None
        with self.assertRaises(RuntimeError, msg='storage root of project test-project is None') as cm:
            with db.session_scope() as session:
                service = ModelService(session)
                model_job = session.query(ModelJob).get(self._MODEL_JOB_ID)
                service.create_model_from_model_job(model_job=model_job)


class ModelJobGroupServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            dataset = Dataset(id=1, name='name', uuid='uuid')
            project = Project(id=1, name='project')
            group = ModelJobGroup(id=1, name='group', project_id=1)
            algorithm_project = AlgorithmProject(id=1, name='name', uuid='algo-uuid')
            session.add_all([dataset, project, group, algorithm_project])
            session.commit()

    @patch('fedlearner_webconsole.composer.composer_service.CronJobService.start_cronjob')
    @patch('fedlearner_webconsole.composer.composer_service.CronJobService.stop_cronjob')
    def test_update_cronjob_config(self, mock_stop_cronjob: Mock, mock_start_cronjob: Mock):
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).get(1)
            ModelJobGroupService(session).update_cronjob_config(group, '')
            self.assertEqual(group.cron_config, '')
            mock_start_cronjob.assert_not_called()
            mock_stop_cronjob.assert_called_once_with(item_name='model_training_cron_job_1')
            mock_stop_cronjob.reset_mock()
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            ModelJobGroupService(session).update_cronjob_config(group, '*/10 * * * *')
            self.assertEqual(group.cron_config, '*/10 * * * *')
            mock_start_cronjob.assert_called_once_with(
                item_name='model_training_cron_job_1',
                items=[(ItemType.MODEL_TRAINING_CRON_JOB,
                        RunnerInput(model_training_cron_job_input=ModelTrainingCronJobInput(group_id=1)))],
                cron_config='*/10 * * * *')
            mock_stop_cronjob.assert_not_called()

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info',
           lambda _: SystemInfo(pure_domain_name='test'))
    def test_create_group(self):
        with db.session_scope() as session:
            service = ModelJobGroupService(session)
            with self.assertRaises(AssertionError, msg='dataset with id 2 is not found'):
                service.create_group(name='name',
                                     uuid='uuid',
                                     project_id=1,
                                     role=ModelJobRole.COORDINATOR,
                                     dataset_id=2,
                                     algorithm_type=AlgorithmType.NN_VERTICAL,
                                     algorithm_project_list=AlgorithmProjectList(),
                                     coordinator_id=1)
        with db.session_scope() as session:
            service = ModelJobGroupService(session)
            with self.assertRaises(Exception, msg='algorithm project must be given if algorithm type is NN_VERTICAL'):
                service.create_group(name='name',
                                     uuid='uuid',
                                     project_id=1,
                                     role=ModelJobRole.COORDINATOR,
                                     dataset_id=1,
                                     algorithm_type=AlgorithmType.NN_VERTICAL,
                                     algorithm_project_list=AlgorithmProjectList(),
                                     coordinator_id=1)
        with db.session_scope() as session:
            service = ModelJobGroupService(session)
            service.create_group(name='name',
                                 uuid='uuid',
                                 project_id=1,
                                 role=ModelJobRole.COORDINATOR,
                                 dataset_id=1,
                                 algorithm_type=AlgorithmType.NN_VERTICAL,
                                 algorithm_project_list=AlgorithmProjectList(algorithm_projects={'test': 'algo-uuid'}),
                                 coordinator_id=1)
            session.commit()
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).filter_by(name='name').first()
            self.assertEqual(group.name, 'name')
            self.assertEqual(group.project_id, 1)
            self.assertEqual(group.role, ModelJobRole.COORDINATOR)
            self.assertEqual(group.dataset_id, 1)
            self.assertEqual(group.algorithm_type, AlgorithmType.NN_VERTICAL)
            self.assertEqual(group.algorithm_project_id, 1)
            self.assertEqual(group.get_algorithm_project_uuid_list(),
                             AlgorithmProjectList(algorithm_projects={'test': 'algo-uuid'}))
            self.assertEqual(group.coordinator_id, 1)

    def test_get_latest_model_from_model_group(self):
        with db.session_scope() as session:
            model_1 = Model()
            model_1.name = 'test_model_name_1'
            model_1.project_id = 1
            model_1.version = 1
            model_1.group_id = 1
            model_2 = Model()
            model_2.name = 'test_model_name_2'
            model_2.project_id = 1
            model_2.version = 2
            model_2.group_id = 1
            session.add_all([model_1, model_2])
            session.commit()
        with db.session_scope() as session:
            service = ModelJobGroupService(session)
            model = service.get_latest_model_from_model_group(1)
            self.assertEqual('test_model_name_2', model.name)

    @patch('fedlearner_webconsole.project.services.SettingService.get_system_info')
    def test_initialize_auth_status(self, mock_system_info):
        mock_system_info.return_value = SystemInfo(pure_domain_name='test', name='name')
        with db.session_scope() as session:
            participant = Participant(id=1, name='party', domain_name='fl-peer.com', host='127.0.0.1', port=32443)
            relationship = ProjectParticipant(project_id=1, participant_id=1)
            session.add_all([participant, relationship])
            session.commit()
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            ModelJobGroupService(session).initialize_auth_status(group)
            session.commit()
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            self.assertEqual(
                group.get_participants_info(),
                ParticipantsInfo(
                    participants_map={
                        'peer': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                        'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                    }))


if __name__ == '__main__':
    unittest.main()

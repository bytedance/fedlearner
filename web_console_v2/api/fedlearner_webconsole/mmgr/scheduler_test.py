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

# pylint: disable=protected-access
import grpc
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock, call, ANY
from google.protobuf.struct_pb2 import Value

from testing.common import NoWebServerTestCase
from testing.rpc.client import FakeRpcError
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import Dataset, DataBatch
from fedlearner_webconsole.initial_db import _insert_or_update_templates
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.mmgr.models import ModelJob, ModelJobRole, ModelJobStatus, ModelJobType, ModelJobGroup, \
    GroupCreateStatus, GroupAutoUpdateStatus, Model, AuthStatus
from fedlearner_webconsole.mmgr.scheduler import ModelJobSchedulerRunner, ModelJobGroupSchedulerRunner, \
    ModelJobGroupLongPeriodScheduler
from fedlearner_webconsole.composer.interface import RunnerStatus, RunnerContext
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobGlobalConfig, ModelJobConfig, AlgorithmProjectList
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, JobDefinition
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, RunnerOutput
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus


class ModelJobSchedulerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='test')
            participant = Participant(id=1, name='party', domain_name='fl-peer.com')
            project_participant = ProjectParticipant(project_id=1, participant_id=1)
            _insert_or_update_templates(session)
            g1 = ModelJobGroup(id=1, name='g1', uuid='group-uuid')
            m1 = ModelJob(id=1,
                          name='j1',
                          role=ModelJobRole.COORDINATOR,
                          status=ModelJobStatus.PENDING,
                          model_job_type=ModelJobType.TRAINING,
                          algorithm_type=AlgorithmType.NN_VERTICAL,
                          dataset_id=1,
                          project_id=1)
            m1.set_global_config(ModelJobGlobalConfig(global_config={'test': ModelJobConfig(algorithm_uuid='uuid')}))
            m2 = ModelJob(id=2,
                          name='j2',
                          model_job_type=ModelJobType.TRAINING,
                          role=ModelJobRole.PARTICIPANT,
                          status=ModelJobStatus.PENDING)
            m3 = ModelJob(id=3,
                          name='j3',
                          role=ModelJobRole.COORDINATOR,
                          status=ModelJobStatus.CONFIGURED,
                          project_id=1,
                          uuid='uuid',
                          group_id=1,
                          version=3,
                          model_job_type=ModelJobType.TRAINING,
                          algorithm_type=AlgorithmType.NN_VERTICAL)
            m3.set_global_config(ModelJobGlobalConfig(global_config={'test': ModelJobConfig(algorithm_uuid='uuid')}))
            m4 = ModelJob(id=4, name='j4', role=ModelJobRole.PARTICIPANT, status=ModelJobStatus.CONFIGURED)
            m5 = ModelJob(id=5, name='j5', role=ModelJobRole.PARTICIPANT, status=ModelJobStatus.RUNNING)
            m6 = ModelJob(id=6,
                          name='j6',
                          role=ModelJobRole.COORDINATOR,
                          status=ModelJobStatus.PENDING,
                          model_job_type=ModelJobType.EVALUATION,
                          auth_status=AuthStatus.AUTHORIZED)
            participants_info = ParticipantsInfo(
                participants_map={
                    'demo1': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'demo2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                })
            m6.set_participants_info(participants_info)
            m7 = ModelJob(id=7,
                          name='j7',
                          role=ModelJobRole.PARTICIPANT,
                          status=ModelJobStatus.RUNNING,
                          model_job_type=ModelJobType.PREDICTION,
                          auth_status=AuthStatus.AUTHORIZED)
            participants_info = ParticipantsInfo(
                participants_map={
                    'demo1': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'demo2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                })
            m7.set_participants_info(participants_info)
            m8 = ModelJob(id=8,
                          name='j8',
                          role=ModelJobRole.PARTICIPANT,
                          status=ModelJobStatus.PENDING,
                          model_job_type=ModelJobType.EVALUATION,
                          auth_status=AuthStatus.PENDING)
            participants_info = ParticipantsInfo(
                participants_map={
                    'demo1': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'demo2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                })
            m8.set_participants_info(participants_info)
            m9 = ModelJob(id=9,
                          name='j9',
                          role=ModelJobRole.PARTICIPANT,
                          status=ModelJobStatus.PENDING,
                          model_job_type=ModelJobType.PREDICTION,
                          auth_status=AuthStatus.AUTHORIZED)
            participants_info = ParticipantsInfo(
                participants_map={
                    'demo1': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'demo2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                })
            m9.set_participants_info(participants_info)
            session.add_all([project, participant, project_participant, g1, m1, m2, m3, m4, m5, m6, m7, m8, m9])
            session.commit()

    @patch('fedlearner_webconsole.mmgr.model_job_configer.ModelJobConfiger.set_dataset')
    @patch('fedlearner_webconsole.mmgr.service.ModelJobService._get_job')
    @patch('fedlearner_webconsole.mmgr.scheduler.ModelJobConfiger')
    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    def test_config_model_job(self, mock_system_info: MagicMock, mock_configer: MagicMock, mock_get_job: MagicMock,
                              mock_set_dataset: MagicMock):
        mock_system_info.return_value = SystemInfo(pure_domain_name='test')
        mock_get_job.return_value = Job(id=1, name='job')
        instance = mock_configer.return_value
        instance.get_config.return_value = WorkflowDefinition(job_definitions=[JobDefinition(name='nn-model')])
        scheduler = ModelJobSchedulerRunner()
        scheduler._config_model_job(model_job_id=1)
        mock_configer.assert_called_with(session=ANY,
                                         model_job_type=ModelJobType.TRAINING,
                                         algorithm_type=AlgorithmType.NN_VERTICAL,
                                         project_id=1)
        instance.get_config.assert_called_with(dataset_id=1,
                                               model_id=None,
                                               model_job_config=ModelJobConfig(algorithm_uuid='uuid'))
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            self.assertEqual(model_job.status, ModelJobStatus.CONFIGURED)

    def test_config_model_job_with_no_global_config(self):
        with db.session_scope() as session:
            workflow = Workflow(id=1, name='workflow', uuid='uuid', state=WorkflowState.RUNNING)
            model_job = session.query(ModelJob).get(2)
            model_job.workflow_uuid = 'uuid'
            session.add(workflow)
            session.commit()
        scheduler = ModelJobSchedulerRunner()
        scheduler._config_model_job(model_job_id=2)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(2)
            self.assertEqual(model_job.status, ModelJobStatus.RUNNING)

    def test_check_model_job(self):
        ModelJobSchedulerRunner._check_model_job(model_job_id=3)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(3)
            self.assertEqual(model_job.status, ModelJobStatus.CONFIGURED)
            workflow = Workflow(id=1, state=WorkflowState.READY)
            model_job.workflow_id = 1
            session.add(workflow)
            session.commit()
        ModelJobSchedulerRunner._check_model_job(model_job_id=3)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(3)
            self.assertEqual(model_job.status, ModelJobStatus.CONFIGURED)
            workflow = session.query(Workflow).get(1)
            workflow.state = WorkflowState.RUNNING
            session.commit()
        ModelJobSchedulerRunner._check_model_job(model_job_id=3)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(3)
            self.assertEqual(model_job.status, ModelJobStatus.RUNNING)
            workflow = session.query(Workflow).get(1)
            workflow.state = WorkflowState.FAILED
            session.commit()
        ModelJobSchedulerRunner._check_model_job(model_job_id=3)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(3)
            self.assertEqual(model_job.status, ModelJobStatus.FAILED)

    @patch('fedlearner_webconsole.mmgr.scheduler.ModelJobSchedulerRunner._check_model_job')
    @patch('fedlearner_webconsole.mmgr.scheduler.ModelJobSchedulerRunner._config_model_job')
    def test_schedule_model_job(self, mock_config: MagicMock, mock_check_job: MagicMock):
        scheduler = ModelJobSchedulerRunner()
        scheduler.schedule_model_job()
        mock_config.assert_has_calls(
            calls=[call(
                model_job_id=1), call(model_job_id=2),
                   call(model_job_id=6),
                   call(model_job_id=9)])
        mock_check_job.assert_has_calls(calls=[call(model_job_id=3), call(model_job_id=4), call(model_job_id=5)])

    @patch('fedlearner_webconsole.mmgr.scheduler.ModelJobSchedulerRunner.schedule_model_job')
    def test_run(self, mock_schedule_model_job: MagicMock):
        scheduler = ModelJobSchedulerRunner()
        runner_input = RunnerInput()
        runner_context = RunnerContext(index=0, input=runner_input)
        runner_status, runner_output = scheduler.run(runner_context)
        mock_schedule_model_job.assert_called()
        mock_schedule_model_job.reset_mock()
        self.assertEqual(runner_output, RunnerOutput())
        self.assertEqual(runner_status, RunnerStatus.DONE)

        def side_effect():
            raise Exception('haha')

        mock_schedule_model_job.side_effect = side_effect
        scheduler = ModelJobSchedulerRunner()
        runner_status, runner_output = scheduler.run(runner_context)
        mock_schedule_model_job.assert_called()
        self.assertEqual(runner_output, RunnerOutput(error_message='haha'))
        self.assertEqual(runner_status, RunnerStatus.FAILED)


class ModelJobGroupSchedulerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant = Participant(id=1, name='peer', domain_name='fl-peer.com')
            project_participant = ProjectParticipant(id=1, project_id=1, participant_id=1)
            dataset = Dataset(id=1, uuid='dataset_uuid', name='dataset')
            algorithm_project_list = AlgorithmProjectList()
            algorithm_project_list.algorithm_projects['test'] = 'algorithm-project-uuid1'
            algorithm_project_list.algorithm_projects['peer'] = 'algorithm-project-uuid2'
            group1 = ModelJobGroup(id=1,
                                   project_id=1,
                                   uuid='uuid1',
                                   name='group1',
                                   status=GroupCreateStatus.PENDING,
                                   ticket_status=TicketStatus.PENDING)
            group2 = ModelJobGroup(id=2,
                                   project_id=1,
                                   uuid='uuid2',
                                   name='group2',
                                   status=GroupCreateStatus.PENDING,
                                   ticket_status=TicketStatus.APPROVED,
                                   algorithm_type=AlgorithmType.NN_VERTICAL,
                                   dataset_id=1,
                                   role=ModelJobRole.COORDINATOR)
            group2.set_algorithm_project_uuid_list(algorithm_project_list)
            group3 = ModelJobGroup(id=3,
                                   project_id=1,
                                   uuid='uuid3',
                                   name='group3',
                                   status=GroupCreateStatus.PENDING,
                                   ticket_status=TicketStatus.APPROVED,
                                   algorithm_type=AlgorithmType.NN_HORIZONTAL,
                                   dataset_id=1,
                                   role=ModelJobRole.COORDINATOR)
            group4 = ModelJobGroup(id=4,
                                   project_id=1,
                                   uuid='uuid4',
                                   name='group',
                                   status=GroupCreateStatus.PENDING,
                                   ticket_status=TicketStatus.APPROVED,
                                   role=ModelJobRole.PARTICIPANT)
            group5 = ModelJobGroup(id=5,
                                   project_id=1,
                                   uuid='uuid5',
                                   name='group5',
                                   status=GroupCreateStatus.SUCCEEDED,
                                   ticket_status=TicketStatus.APPROVED)
            group6 = ModelJobGroup(id=6,
                                   project_id=1,
                                   uuid='uuid6',
                                   name='group6',
                                   status=GroupCreateStatus.FAILED,
                                   ticket_status=TicketStatus.APPROVED)
            session.add_all(
                [project, participant, project_participant, dataset, group1, group2, group3, group4, group5, group6])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.create_model_job_group')
    def test_create_model_job_group_for_participants(self, mock_client: MagicMock):
        scheduler = ModelJobGroupSchedulerRunner()
        scheduler._create_model_job_group_for_participants(model_job_group_id=2)
        algorithm_project_list = AlgorithmProjectList()
        algorithm_project_list.algorithm_projects['test'] = 'algorithm-project-uuid1'
        algorithm_project_list.algorithm_projects['peer'] = 'algorithm-project-uuid2'
        mock_client.assert_called_with(name='group2',
                                       uuid='uuid2',
                                       algorithm_type=AlgorithmType.NN_VERTICAL,
                                       dataset_uuid='dataset_uuid',
                                       algorithm_project_list=algorithm_project_list)
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(2)
            self.assertEqual(group.status, GroupCreateStatus.SUCCEEDED)
        mock_client.side_effect = FakeRpcError(grpc.StatusCode.INVALID_ARGUMENT, 'dataset with uuid is not found')
        scheduler._create_model_job_group_for_participants(model_job_group_id=3)
        mock_client.assert_called()
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(3)
            self.assertEqual(group.status, GroupCreateStatus.FAILED)

    @patch('fedlearner_webconsole.mmgr.scheduler.ModelJobGroupSchedulerRunner._create_model_job_group_for_participants')
    def test_schedule_model_job_group(self, mock_create_model_job_group):
        scheduler = ModelJobGroupSchedulerRunner()
        scheduler._schedule_model_job_group()
        mock_create_model_job_group.assert_has_calls(calls=[call(model_job_group_id=2), call(model_job_group_id=3)])

    @patch('fedlearner_webconsole.mmgr.scheduler.ModelJobGroupSchedulerRunner._schedule_model_job_group')
    def test_run(self, mock_schedule_model_job_group: MagicMock):
        scheduler = ModelJobGroupSchedulerRunner()
        runner_input = RunnerInput()
        runner_context = RunnerContext(index=0, input=runner_input)
        runner_status, runner_output = scheduler.run(runner_context)
        mock_schedule_model_job_group.assert_called()
        mock_schedule_model_job_group.reset_mock()
        self.assertEqual(runner_output, RunnerOutput())
        self.assertEqual(runner_status, RunnerStatus.DONE)

        def side_effect():
            raise Exception('haha')

        mock_schedule_model_job_group.side_effect = side_effect
        scheduler = ModelJobGroupSchedulerRunner()
        runner_status, runner_output = scheduler.run(runner_context)
        mock_schedule_model_job_group.assert_called()
        self.assertEqual(runner_output, RunnerOutput(error_message='haha'))
        self.assertEqual(runner_status, RunnerStatus.FAILED)


class ModelJobGroupLongPeriodSchedulerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            data_batch = DataBatch(id=1,
                                   name='20220101-08',
                                   dataset_id=1,
                                   event_time=datetime(year=2000, month=1, day=1, hour=8),
                                   latest_parent_dataset_job_stage_id=1)
            group1 = ModelJobGroup(id=1,
                                   name='group1',
                                   role=ModelJobRole.COORDINATOR,
                                   auto_update_status=GroupAutoUpdateStatus.ACTIVE)
            group2 = ModelJobGroup(id=2,
                                   name='group2',
                                   role=ModelJobRole.COORDINATOR,
                                   auto_update_status=GroupAutoUpdateStatus.INITIAL)
            group3 = ModelJobGroup(id=3,
                                   name='group3',
                                   role=ModelJobRole.PARTICIPANT,
                                   auto_update_status=GroupAutoUpdateStatus.ACTIVE)
            group4 = ModelJobGroup(id=4,
                                   name='group4',
                                   role=ModelJobRole.COORDINATOR,
                                   auto_update_status=GroupAutoUpdateStatus.ACTIVE)
            group5 = ModelJobGroup(id=5,
                                   name='group5',
                                   role=ModelJobRole.COORDINATOR,
                                   auto_update_status=GroupAutoUpdateStatus.ACTIVE,
                                   latest_version=4)
            model_job1 = ModelJob(id=1,
                                  group_id=4,
                                  auto_update=True,
                                  created_at=datetime(2022, 12, 16, 1, 0, 0),
                                  status=ModelJobStatus.SUCCEEDED,
                                  data_batch_id=1)
            model_job2 = ModelJob(id=2,
                                  group_id=4,
                                  auto_update=False,
                                  created_at=datetime(2022, 12, 16, 2, 0, 0),
                                  status=ModelJobStatus.SUCCEEDED)
            model_job3 = ModelJob(id=3,
                                  group_id=4,
                                  auto_update=True,
                                  created_at=datetime(2022, 12, 16, 3, 0, 0),
                                  status=ModelJobStatus.RUNNING,
                                  data_batch_id=1)
            model_job4 = ModelJob(id=4,
                                  group_id=5,
                                  auto_update=True,
                                  created_at=datetime(2022, 12, 16, 1, 0, 0),
                                  status=ModelJobStatus.SUCCEEDED,
                                  data_batch_id=1)
            model_job5 = ModelJob(id=5,
                                  group_id=5,
                                  auto_update=False,
                                  created_at=datetime(2022, 12, 16, 2, 0, 0),
                                  status=ModelJobStatus.FAILED)
            global_config = ModelJobGlobalConfig(
                dataset_uuid='uuid',
                global_config={
                    'test1': ModelJobConfig(algorithm_uuid='uuid1', variables=[Variable(name='load_model_name')]),
                    'test2': ModelJobConfig(algorithm_uuid='uuid2', variables=[Variable(name='load_model_name')])
                })
            model_job6 = ModelJob(id=6,
                                  name='model-job6',
                                  group_id=5,
                                  auto_update=True,
                                  created_at=datetime(2022, 12, 16, 3, 0, 0),
                                  status=ModelJobStatus.SUCCEEDED,
                                  data_batch_id=1,
                                  role=ModelJobRole.COORDINATOR,
                                  model_job_type=ModelJobType.TRAINING,
                                  algorithm_type=AlgorithmType.NN_VERTICAL,
                                  project_id=1,
                                  comment='comment',
                                  version=3)
            model_job6.set_global_config(global_config)
            session.add_all([
                group1, group2, group3, group4, group5, model_job1, model_job2, model_job3, model_job4, model_job5,
                model_job6, data_batch
            ])
            session.commit()

    @patch('fedlearner_webconsole.mmgr.scheduler.resource_uuid')
    @patch('fedlearner_webconsole.mmgr.service.ModelJobService.create_model_job')
    @patch('fedlearner_webconsole.dataset.services.BatchService.get_next_batch')
    def test_create_auto_update_model_job(self, mock_get_next_batch: MagicMock, mock_create_model_job: MagicMock,
                                          mock_resource_uuid: MagicMock):
        scheduler = ModelJobGroupLongPeriodScheduler()
        # fail due to model job is None
        scheduler._create_auto_update_model_job(model_job_group_id=1)
        mock_create_model_job.assert_not_called()
        # fail due to model job status is not SUCCEEDED
        scheduler._create_auto_update_model_job(model_job_group_id=4)
        mock_create_model_job.assert_not_called()
        # fail due to next data batch is None
        mock_get_next_batch.return_value = None
        scheduler._create_auto_update_model_job(model_job_group_id=5)
        mock_create_model_job.assert_not_called()
        # create auto model job failed due to model_name is None
        mock_get_next_batch.return_value = DataBatch(id=2)
        mock_resource_uuid.return_value = 'uuid'
        with self.assertRaises(Exception):
            scheduler._create_auto_update_model_job(model_job_group_id=5)
        with db.session_scope() as session:
            model = Model(id=1, name='model-job6', uuid='uuid')
            session.add(model)
            session.commit()
        scheduler._create_auto_update_model_job(model_job_group_id=5)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='model-job6').first()
            self.assertEqual(model_job.model_id, 1)
        global_config = ModelJobGlobalConfig(
            dataset_uuid='uuid',
            global_config={
                'test1':
                    ModelJobConfig(algorithm_uuid='uuid1',
                                   variables=[
                                       Variable(name='load_model_name',
                                                value='model-job6',
                                                value_type=Variable.ValueType.STRING,
                                                typed_value=Value(string_value='model-job6'))
                                   ]),
                'test2':
                    ModelJobConfig(algorithm_uuid='uuid2',
                                   variables=[
                                       Variable(name='load_model_name',
                                                value='model-job6',
                                                value_type=Variable.ValueType.STRING,
                                                typed_value=Value(string_value='model-job6'))
                                   ])
            })
        mock_create_model_job.assert_called_with(name='group5-v5',
                                                 uuid='uuid',
                                                 role=ModelJobRole.COORDINATOR,
                                                 model_job_type=ModelJobType.TRAINING,
                                                 algorithm_type=AlgorithmType.NN_VERTICAL,
                                                 global_config=global_config,
                                                 group_id=5,
                                                 project_id=1,
                                                 data_batch_id=2,
                                                 comment='comment',
                                                 version=5)

    @patch('fedlearner_webconsole.mmgr.scheduler.ModelJobGroupLongPeriodScheduler._create_auto_update_model_job')
    def test_schedule_model_job_group(self, mock_create_auto_update_model_job: MagicMock):
        scheduler = ModelJobGroupLongPeriodScheduler()
        scheduler._schedule_model_job_group()
        mock_create_auto_update_model_job.assert_has_calls(
            calls=[call(model_job_group_id=1),
                   call(model_job_group_id=4),
                   call(model_job_group_id=5)])

    @patch('fedlearner_webconsole.mmgr.scheduler.ModelJobGroupLongPeriodScheduler._schedule_model_job_group')
    def test_run(self, mock_schedule_model_job_group: MagicMock):
        scheduler = ModelJobGroupLongPeriodScheduler()
        runner_input = RunnerInput()
        runner_context = RunnerContext(index=0, input=runner_input)
        runner_status, runner_output = scheduler.run(runner_context)
        mock_schedule_model_job_group.assert_called()
        mock_schedule_model_job_group.reset_mock()
        self.assertEqual(runner_output, RunnerOutput())
        self.assertEqual(runner_status, RunnerStatus.DONE)


if __name__ == '__main__':
    unittest.main()

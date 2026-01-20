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
from datetime import datetime
import unittest
from unittest.mock import MagicMock, patch
from google.protobuf.struct_pb2 import Value

from testing.no_web_server_test_case import NoWebServerTestCase
from testing.dataset import FakeDatasetJobConfiger
from fedlearner_webconsole.exceptions import InternalException
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.utils.const import SYSTEM_WORKFLOW_CREATOR_USERNAME
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.controllers import DatasetJobController, DatasetJobStageController
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobKind, DatasetJobStage, DatasetJobState
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto import dataset_pb2, service_pb2
from fedlearner_webconsole.proto.rpc.v2 import job_service_pb2
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.proto.two_pc_pb2 import LaunchDatasetJobData, LaunchDatasetJobStageData, \
    StopDatasetJobData, StopDatasetJobStageData, TransactionData, TwoPcType
from fedlearner_webconsole.proto.project_pb2 import ParticipantInfo, ParticipantsInfo
from fedlearner_webconsole.proto.rpc.v2.resource_service_pb2 import ListDatasetsResponse


def get_dataset_job_pb(*args, **kwargs) -> service_pb2.GetDatasetJobResponse:
    dataset_job = dataset_pb2.DatasetJob(uuid='u1234')
    global_configs = dataset_pb2.DatasetJobGlobalConfigs()
    global_configs.global_configs['test_domain'].MergeFrom(
        dataset_pb2.DatasetJobConfig(dataset_uuid=resource_uuid(),
                                     variables=[
                                         Variable(name='hello',
                                                  value_type=Variable.ValueType.NUMBER,
                                                  typed_value=Value(number_value=1)),
                                         Variable(name='test',
                                                  value_type=Variable.ValueType.STRING,
                                                  typed_value=Value(string_value='test_value')),
                                     ]))
    dataset_job.global_configs.MergeFrom(global_configs)
    return service_pb2.GetDatasetJobResponse(dataset_job=dataset_job)


class DatasetJobControllerTest(NoWebServerTestCase):
    _PROJECT_ID = 1
    _PARTICIPANT_ID = 1
    _OUTPUT_DATASET_ID = 1

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=self._PROJECT_ID, name='test-project')
            participant = Participant(id=self._PARTICIPANT_ID, name='participant_1', domain_name='fake_domain_name_1')
            project_participant = ProjectParticipant(project_id=self._PROJECT_ID, participant_id=self._PARTICIPANT_ID)
            session.add(project)
            session.add(participant)
            session.add(project_participant)
            output_dataset = Dataset(id=self._OUTPUT_DATASET_ID,
                                     name='test_output_dataset',
                                     uuid=resource_uuid(),
                                     path='/data/dataset/test_dataset')
            session.add(output_dataset)
            session.commit()

    @patch('fedlearner_webconsole.dataset.services.DatasetJobService.need_distribute')
    @patch('fedlearner_webconsole.dataset.controllers.TransactionManager')
    def test_transfer_state(self, mock_transaction_manager: MagicMock, mock_need_distribute: MagicMock):
        dataset_job_id = 10
        workflow_id = 11
        with db.session_scope() as session:
            uuid = resource_uuid()
            workflow = Workflow(id=workflow_id, uuid=uuid)
            dataset_job = DatasetJob(id=dataset_job_id,
                                     uuid=uuid,
                                     kind=DatasetJobKind.IMPORT_SOURCE,
                                     project_id=self._PROJECT_ID,
                                     workflow_id=workflow_id,
                                     input_dataset_id=1,
                                     output_dataset_id=2)
            session.add(workflow)
            session.add(dataset_job)
            session.commit()

        mock_need_distribute.return_value = False
        mock_run = MagicMock(return_value=(True, ''))
        mock_transaction_manager.return_value = MagicMock(run=mock_run)

        # test illegal target state
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(dataset_job_id)
            with self.assertRaises(InternalException):
                DatasetJobController(session)._transfer_state(uuid=dataset_job.uuid,
                                                              target_state=DatasetJobState.SUCCEEDED)
            mock_transaction_manager.assert_not_called()

        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(dataset_job_id)
            DatasetJobController(session)._transfer_state(uuid=dataset_job.uuid, target_state=DatasetJobState.RUNNING)
            data = LaunchDatasetJobData(dataset_job_uuid=dataset_job.uuid)
            mock_run.assert_called_with(data=TransactionData(launch_dataset_job_data=data))
            mock_transaction_manager.assert_called_with(project_name='test-project',
                                                        project_token=None,
                                                        two_pc_type=TwoPcType.LAUNCH_DATASET_JOB,
                                                        participants=[])

        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(dataset_job_id)
            DatasetJobController(session)._transfer_state(uuid=dataset_job.uuid, target_state=DatasetJobState.STOPPED)
            data = StopDatasetJobData(dataset_job_uuid=dataset_job.uuid)
            mock_run.assert_called_with(data=TransactionData(stop_dataset_job_data=data))
            mock_transaction_manager.assert_called_with(project_name='test-project',
                                                        project_token=None,
                                                        two_pc_type=TwoPcType.STOP_DATASET_JOB,
                                                        participants=[])

        mock_need_distribute.return_value = True
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(dataset_job_id)
            DatasetJobController(session)._transfer_state(uuid=dataset_job.uuid, target_state=DatasetJobState.RUNNING)
            data = LaunchDatasetJobData(dataset_job_uuid=dataset_job.uuid)
            mock_run.assert_called_with(data=TransactionData(launch_dataset_job_data=data))
            mock_transaction_manager.assert_called_with(project_name='test-project',
                                                        project_token=None,
                                                        two_pc_type=TwoPcType.LAUNCH_DATASET_JOB,
                                                        participants=['fake_domain_name_1'])

        mock_run = MagicMock(return_value=(False, ''))
        mock_transaction_manager.return_value = MagicMock(run=mock_run)
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(dataset_job_id)
            with self.assertRaises(InternalException):
                DatasetJobController(session)._transfer_state(uuid=dataset_job.uuid,
                                                              target_state=DatasetJobState.RUNNING)

    @patch('fedlearner_webconsole.dataset.controllers.DatasetJobController._transfer_state')
    def test_start(self, mock_transfer_state: MagicMock):
        with db.session_scope() as session:
            DatasetJobController(session).start(uuid=1)
        mock_transfer_state.assert_called_once_with(uuid=1, target_state=DatasetJobState.RUNNING)

    @patch('fedlearner_webconsole.dataset.controllers.DatasetJobController._transfer_state')
    @patch('fedlearner_webconsole.dataset.controllers.DatasetJobStageController.stop')
    def test_stop(self, mock_dataset_job_stage_stop: MagicMock, mock_transfer_state: MagicMock):
        with db.session_scope() as session:
            dataset_job = DatasetJob(
                id=1,
                uuid='u54321',
                project_id=1,
                kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                input_dataset_id=123,
                output_dataset_id=0,
                coordinator_id=0,
            )
            session.add(dataset_job)
            dataset_job_stage_1 = DatasetJobStage(id=1,
                                                  uuid='job_stage uuid_1',
                                                  name='default dataset job stage 1',
                                                  project_id=1,
                                                  workflow_id=1,
                                                  created_at=datetime(2022, 1, 1, 0, 0, 0),
                                                  dataset_job_id=1,
                                                  data_batch_id=1,
                                                  event_time=datetime(2022, 1, 1),
                                                  state=DatasetJobState.PENDING)
            session.add(dataset_job_stage_1)
            dataset_job_stage_2 = DatasetJobStage(id=2,
                                                  uuid='job_stage uuid_2',
                                                  name='default dataset job stage 2',
                                                  project_id=1,
                                                  workflow_id=1,
                                                  created_at=datetime(2022, 1, 2, 0, 0, 0),
                                                  dataset_job_id=1,
                                                  data_batch_id=1,
                                                  event_time=datetime(2022, 1, 2),
                                                  state=DatasetJobState.SUCCEEDED)
            session.add(dataset_job_stage_2)
            session.commit()
        with db.session_scope() as session:
            DatasetJobController(session).stop(uuid='u54321')
        mock_transfer_state.assert_called_once_with(uuid='u54321', target_state=DatasetJobState.STOPPED)
        mock_dataset_job_stage_stop.assert_called_once_with(uuid='job_stage uuid_1')

    @patch('fedlearner_webconsole.dataset.controllers.ResourceServiceClient.inform_dataset')
    @patch('fedlearner_webconsole.dataset.controllers.DatasetJobService.get_participants_need_distribute')
    def test_inform_auth_status(self, mock_get_participants_need_distribute: MagicMock, mock_inform_dataset: MagicMock):
        particiapnt = Participant(id=1, name='test_participant', domain_name='fl-test-domain-name.com')
        mock_get_participants_need_distribute.return_value = [particiapnt]
        with db.session_scope() as session:
            dataset_job = DatasetJob(
                id=1,
                uuid='u54321',
                project_id=1,
                kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                input_dataset_id=123,
                output_dataset_id=self._OUTPUT_DATASET_ID,
                coordinator_id=0,
            )
            session.add(dataset_job)
            session.flush()
            DatasetJobController(session=session).inform_auth_status(dataset_job=dataset_job,
                                                                     auth_status=AuthStatus.AUTHORIZED)
            mock_inform_dataset.assert_called_once_with(dataset_uuid=dataset_job.output_dataset.uuid,
                                                        auth_status=AuthStatus.AUTHORIZED)

    @patch('fedlearner_webconsole.dataset.controllers.SystemServiceClient.list_flags')
    @patch('fedlearner_webconsole.dataset.controllers.ResourceServiceClient.list_datasets')
    @patch('fedlearner_webconsole.dataset.controllers.DatasetJobService.get_participants_need_distribute')
    def test_update_auth_status_cache(self, mock_get_participants_need_distribute: MagicMock,
                                      mock_list_datasets: MagicMock, mock_list_flags: MagicMock):
        particiapnt = Participant(id=1, name='test_participant', domain_name='fl-test-domain-name.com')
        mock_get_participants_need_distribute.return_value = [particiapnt]
        mock_list_datasets.return_value = ListDatasetsResponse(
            participant_datasets=[dataset_pb2.ParticipantDatasetRef(auth_status=AuthStatus.AUTHORIZED.name)])
        with db.session_scope() as session:
            dataset_job = DatasetJob(
                id=1,
                uuid='u54321',
                project_id=1,
                kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                input_dataset_id=123,
                output_dataset_id=self._OUTPUT_DATASET_ID,
                coordinator_id=0,
            )
            session.add(dataset_job)
            dataset: Dataset = session.query(Dataset).get(self._OUTPUT_DATASET_ID)
            participants_info = ParticipantsInfo(
                participants_map={'test-domain-name': ParticipantInfo(auth_status=AuthStatus.PENDING.name)})
            dataset.set_participants_info(participants_info=participants_info)
            session.flush()
            mock_list_flags.return_value = {'list_datasets_rpc_enabled': False}
            DatasetJobController(session=session).update_auth_status_cache(dataset_job=dataset_job)
            mock_list_datasets.assert_not_called()
            mock_list_flags.reset_mock()
            mock_list_flags.return_value = {'list_datasets_rpc_enabled': True}
            DatasetJobController(session=session).update_auth_status_cache(dataset_job=dataset_job)
            mock_list_datasets.assert_called_once_with(uuid=dataset_job.output_dataset.uuid)
            self.assertEqual(dataset.get_participants_info().participants_map['test-domain-name'].auth_status,
                             AuthStatus.AUTHORIZED.name)


def get_dataset_job_stage_pb(*args, **kwargs) -> job_service_pb2.GetDatasetJobStageResponse:
    dataset_job_stage = dataset_pb2.DatasetJobStage(uuid='dataset_job_stage uuid')
    global_configs = dataset_pb2.DatasetJobGlobalConfigs()
    global_configs.global_configs['test_domain'].MergeFrom(
        dataset_pb2.DatasetJobConfig(dataset_uuid=resource_uuid(),
                                     variables=[
                                         Variable(name='hello',
                                                  value_type=Variable.ValueType.NUMBER,
                                                  typed_value=Value(number_value=1)),
                                         Variable(name='test',
                                                  value_type=Variable.ValueType.STRING,
                                                  typed_value=Value(string_value='test_value')),
                                     ]))
    dataset_job_stage.global_configs.MergeFrom(global_configs)
    return job_service_pb2.GetDatasetJobStageResponse(dataset_job_stage=dataset_job_stage)


class DatasetJobStageControllerTest(NoWebServerTestCase):
    _PROJECT_ID = 1
    _PARTICIPANT_ID = 1
    _OUTPUT_DATASET_ID = 1

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=self._PROJECT_ID, name='test-project')
            participant = Participant(id=self._PARTICIPANT_ID, name='participant_1', domain_name='fake_domain_name_1')
            project_participant = ProjectParticipant(project_id=self._PROJECT_ID, participant_id=self._PARTICIPANT_ID)
            session.add(project)
            session.add(participant)
            session.add(project_participant)
            output_dataset = Dataset(id=self._OUTPUT_DATASET_ID,
                                     name='test_output_dataset',
                                     uuid='output_dataset uuid',
                                     path='/data/dataset/test_dataset')
            session.add(output_dataset)
            session.commit()

    @patch('fedlearner_webconsole.dataset.controllers.DatasetJobConfiger.from_kind',
           lambda *args: FakeDatasetJobConfiger(None))
    @patch('fedlearner_webconsole.dataset.controllers.SettingService.get_system_info',
           lambda: SystemInfo(name='test', domain_name='test_domain.fedlearner.net'))
    def test_create_ready_workflow_coordinator(self):

        with db.session_scope() as session:

            dataset_job = DatasetJob(
                id=1,
                uuid='dataset_job uuid',
                kind=DatasetJobKind.IMPORT_SOURCE,
                coordinator_id=0,
                project_id=self._PROJECT_ID,
                input_dataset_id=0,
                output_dataset_id=self._OUTPUT_DATASET_ID,
            )
            session.add(dataset_job)
            uuid = resource_uuid()
            dataset_job_stage = DatasetJobStage(
                id=1,
                uuid=uuid,
                project_id=self._PROJECT_ID,
                dataset_job_id=1,
                data_batch_id=1,
                coordinator_id=0,
            )
            session.add(dataset_job_stage)

            global_configs = dataset_pb2.DatasetJobGlobalConfigs()
            global_configs.global_configs['test_domain'].MergeFrom(
                dataset_pb2.DatasetJobConfig(dataset_uuid=resource_uuid(),
                                             variables=[
                                                 Variable(name='hello',
                                                          value_type=Variable.ValueType.NUMBER,
                                                          typed_value=Value(number_value=1)),
                                                 Variable(name='test',
                                                          value_type=Variable.ValueType.STRING,
                                                          typed_value=Value(string_value='test_value')),
                                             ]))
            dataset_job_stage.set_global_configs(global_configs)
            session.flush()

            wf = DatasetJobStageController(session).create_ready_workflow(dataset_job_stage)
            self.assertEqual(wf.uuid, uuid)
            self.assertEqual(wf.creator, SYSTEM_WORKFLOW_CREATOR_USERNAME)

    @patch('fedlearner_webconsole.dataset.controllers.JobServiceClient.get_dataset_job_stage')
    @patch('fedlearner_webconsole.dataset.job_configer.import_source_configer.ImportSourceConfiger.'\
        'config_local_variables')
    @patch('fedlearner_webconsole.dataset.controllers.SettingService.get_system_info',
           lambda: SystemInfo(name='test', domain_name='test_domain.fedlearner.net'))
    def test_create_ready_workflow_participant(self, mock_config_local_variables: MagicMock,
                                               mock_get_dataset_job_stage: MagicMock):
        get_dataset_job_stage_response = get_dataset_job_stage_pb()
        mock_get_dataset_job_stage.return_value = get_dataset_job_stage_response
        mock_config_local_variables.return_value = get_dataset_job_stage_response.dataset_job_stage.global_configs
        with db.session_scope() as session:
            dataset_job = DatasetJob(
                id=1,
                uuid='dataset_job uuid',
                kind=DatasetJobKind.IMPORT_SOURCE,
                coordinator_id=0,
                project_id=self._PROJECT_ID,
                input_dataset_id=0,
                output_dataset_id=self._OUTPUT_DATASET_ID,
            )
            session.add(dataset_job)
            uuid = resource_uuid()
            dataset_job_stage = DatasetJobStage(
                id=1,
                uuid=uuid,
                project_id=self._PROJECT_ID,
                dataset_job_id=1,
                data_batch_id=1,
                event_time=datetime(2022, 1, 1),
                coordinator_id=self._PARTICIPANT_ID,
            )
            session.add(dataset_job_stage)
            session.flush()

            wf = DatasetJobStageController(session).create_ready_workflow(dataset_job_stage)
            self.assertEqual(wf.uuid, uuid)
            self.assertEqual(wf.creator, SYSTEM_WORKFLOW_CREATOR_USERNAME)
            mock_config_local_variables.assert_called_once_with(
                get_dataset_job_stage_response.dataset_job_stage.global_configs, 'output_dataset uuid',
                datetime(2022, 1, 1))

    @patch('fedlearner_webconsole.dataset.services.DatasetJobService.get_participants_need_distribute')
    @patch('fedlearner_webconsole.dataset.controllers.TransactionManager')
    def test_transfer_state(self, mock_transaction_manager: MagicMock,
                            mock_get_participants_need_distribute: MagicMock):
        dataset_job_id = 10
        dataset_job_stage_id = 11
        workflow_id = 12
        with db.session_scope() as session:
            uuid = resource_uuid()
            workflow = Workflow(id=workflow_id, uuid=uuid)
            dataset_job = DatasetJob(id=dataset_job_id,
                                     uuid=resource_uuid(),
                                     kind=DatasetJobKind.IMPORT_SOURCE,
                                     project_id=self._PROJECT_ID,
                                     input_dataset_id=1,
                                     output_dataset_id=2)
            dataset_job_stage = DatasetJobStage(id=dataset_job_stage_id,
                                                name='stage_1',
                                                uuid=uuid,
                                                dataset_job_id=dataset_job_id,
                                                workflow_id=workflow_id,
                                                project_id=self._PROJECT_ID,
                                                data_batch_id=1,
                                                state=DatasetJobState.PENDING)
            session.add(workflow)
            session.add(dataset_job)
            session.add(dataset_job_stage)
            session.commit()

        mock_get_participants_need_distribute.return_value = []
        mock_run = MagicMock(return_value=(True, ''))
        mock_transaction_manager.return_value = MagicMock(run=mock_run)

        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_id)
            DatasetJobStageController(session)._transfer_state(uuid=dataset_job_stage.uuid,
                                                               target_state=DatasetJobState.RUNNING)
            data = LaunchDatasetJobStageData(dataset_job_stage_uuid=dataset_job_stage.uuid)
            mock_run.assert_called_with(data=TransactionData(launch_dataset_job_stage_data=data))
            mock_transaction_manager.assert_called_with(project_name='test-project',
                                                        project_token=None,
                                                        two_pc_type=TwoPcType.LAUNCH_DATASET_JOB_STAGE,
                                                        participants=[])

        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_id)
            DatasetJobStageController(session)._transfer_state(uuid=dataset_job_stage.uuid,
                                                               target_state=DatasetJobState.STOPPED)
            data = StopDatasetJobStageData(dataset_job_stage_uuid=dataset_job_stage.uuid)
            mock_run.assert_called_with(data=TransactionData(stop_dataset_job_stage_data=data))
            mock_transaction_manager.assert_called_with(project_name='test-project',
                                                        project_token=None,
                                                        two_pc_type=TwoPcType.STOP_DATASET_JOB_STAGE,
                                                        participants=[])

        mock_get_participants_need_distribute.return_value = [Participant(domain_name='fake_domain_name_1')]
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_id)
            DatasetJobStageController(session)._transfer_state(uuid=dataset_job_stage.uuid,
                                                               target_state=DatasetJobState.RUNNING)
            data = LaunchDatasetJobStageData(dataset_job_stage_uuid=dataset_job_stage.uuid)
            mock_run.assert_called_with(data=TransactionData(launch_dataset_job_stage_data=data))
            mock_transaction_manager.assert_called_with(project_name='test-project',
                                                        project_token=None,
                                                        two_pc_type=TwoPcType.LAUNCH_DATASET_JOB_STAGE,
                                                        participants=['fake_domain_name_1'])

        mock_run = MagicMock(return_value=(False, ''))
        mock_transaction_manager.return_value = MagicMock(run=mock_run)
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_id)
            with self.assertRaises(InternalException):
                DatasetJobStageController(session)._transfer_state(uuid=dataset_job_stage.uuid,
                                                                   target_state=DatasetJobState.RUNNING)

    @patch('fedlearner_webconsole.dataset.controllers.DatasetJobStageController._transfer_state')
    def test_start(self, mock_transfer_state: MagicMock):
        with db.session_scope() as session:
            DatasetJobStageController(session).start(uuid=1)
        mock_transfer_state.assert_called_once_with(uuid=1, target_state=DatasetJobState.RUNNING)

    @patch('fedlearner_webconsole.dataset.controllers.DatasetJobStageController._transfer_state')
    def test_stop(self, mock_transfer_state: MagicMock):
        with db.session_scope() as session:
            DatasetJobStageController(session).stop(uuid=1)
        mock_transfer_state.assert_called_once_with(uuid=1, target_state=DatasetJobState.STOPPED)


if __name__ == '__main__':
    unittest.main()

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
import tempfile
import unittest
import urllib.parse
from io import BytesIO
from pathlib import Path
from http import HTTPStatus
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock, call
from envs import Envs
from testing.common import BaseTestCase
from testing.fake_model_job_config import get_global_config, get_workflow_config
from google.protobuf.wrappers_pb2 import BoolValue
from google.protobuf.empty_pb2 import Empty
from google.protobuf.struct_pb2 import Value

from fedlearner_webconsole.db import db
from fedlearner_webconsole.initial_db import _insert_or_update_templates
from fedlearner_webconsole.utils.flask_utils import to_dict
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.participant.models import ProjectParticipant
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.mmgr.models import Model, ModelJob, ModelJobGroup, ModelJobType, ModelJobRole, AuthStatus,\
    ModelJobStatus, GroupAutoUpdateStatus
from fedlearner_webconsole.algorithm.models import AlgorithmType, Algorithm
from fedlearner_webconsole.workflow_template.utils import make_variable
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, JobDefinition
from fedlearner_webconsole.proto.service_pb2 import GetModelJobResponse
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobGlobalConfig, ModelJobConfig, ModelJobPb
from fedlearner_webconsole.workflow.models import WorkflowState, TransactionState
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobKind, DatasetType, DatasetJobState, \
    DatasetJobStage, DataBatch


class ModelJobsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        Envs.SYSTEM_INFO = '{"domain_name": "fl-test.com"}'
        with db.session_scope() as session:
            _insert_or_update_templates(session)
            dataset_job = DatasetJob(id=1,
                                     name='datasetjob',
                                     uuid='dataset-job-uuid',
                                     state=DatasetJobState.SUCCEEDED,
                                     project_id=1,
                                     input_dataset_id=3,
                                     output_dataset_id=1,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN)
            dataset_job_stage = DatasetJobStage(id=1,
                                                name='data-join',
                                                uuid='dataset-job-stage-uuid',
                                                project_id=1,
                                                state=DatasetJobState.SUCCEEDED,
                                                dataset_job_id=1,
                                                data_batch_id=1)
            data_batch = DataBatch(id=1,
                                   name='20221213',
                                   dataset_id=1,
                                   path='/data/dataset/haha/batch/20221213',
                                   latest_parent_dataset_job_stage_id=1,
                                   event_time=datetime(2022, 12, 13, 16, 37, 37))
            dataset = Dataset(id=1,
                              uuid='uuid',
                              name='dataset',
                              dataset_type=DatasetType.PSI,
                              path='/data/dataset/haha',
                              is_published=True)
            project = Project(id=1, name='test-project')
            participant = Participant(id=1, name='peer', domain_name='fl-peer.com')
            pro_participant = ProjectParticipant(id=1, project_id=1, participant_id=1)
            group = ModelJobGroup(id=1, name='test-group', project_id=project.id, uuid='uuid', latest_version=2)
            session.add_all([project, group, dataset, dataset_job, data_batch, dataset_job_stage])
            participants_info = ParticipantsInfo()
            w1 = Workflow(name='w1',
                          uuid='u1',
                          state=WorkflowState.NEW,
                          target_state=WorkflowState.READY,
                          transaction_state=TransactionState.PARTICIPANT_PREPARE)
            mj1 = ModelJob(name='mj1',
                           workflow_uuid=w1.uuid,
                           project_id=1,
                           group_id=1,
                           algorithm_type=AlgorithmType.NN_VERTICAL,
                           model_job_type=ModelJobType.TRAINING,
                           role=ModelJobRole.COORDINATOR,
                           auth_status=AuthStatus.PENDING,
                           created_at=datetime(2022, 8, 4, 0, 0, 0))
            mj1.set_participants_info(participants_info)
            w2 = Workflow(name='w2', uuid='u2', state=WorkflowState.READY, target_state=None)
            w2.set_config(get_workflow_config(model_job_type=ModelJobType.EVALUATION))
            mj2 = ModelJob(name='mj2',
                           workflow_uuid=w2.uuid,
                           project_id=1,
                           group_id=2,
                           algorithm_type=AlgorithmType.TREE_VERTICAL,
                           model_job_type=ModelJobType.EVALUATION,
                           role=ModelJobRole.PARTICIPANT,
                           auth_status=AuthStatus.AUTHORIZED,
                           created_at=datetime(2022, 8, 4, 0, 0, 1))
            mj2.set_participants_info(participants_info)
            w3 = Workflow(name='w3', uuid='u3', state=WorkflowState.RUNNING, target_state=None)
            w3.set_config(get_workflow_config(model_job_type=ModelJobType.PREDICTION))
            mj3 = ModelJob(name='mj3',
                           workflow_uuid=w3.uuid,
                           project_id=1,
                           algorithm_type=AlgorithmType.NN_HORIZONTAL,
                           model_job_type=ModelJobType.PREDICTION,
                           role=ModelJobRole.COORDINATOR,
                           auth_status=AuthStatus.PENDING,
                           created_at=datetime(2022, 8, 4, 0, 0, 2))
            mj3.set_participants_info(participants_info)
            w4 = Workflow(name='w4', uuid='u4', state=WorkflowState.RUNNING, target_state=None)
            w4.set_config(get_workflow_config(model_job_type=ModelJobType.PREDICTION))
            mj4 = ModelJob(name='mj31',
                           workflow_uuid=w4.uuid,
                           project_id=1,
                           algorithm_type=AlgorithmType.TREE_VERTICAL,
                           model_job_type=ModelJobType.PREDICTION,
                           role=ModelJobRole.PARTICIPANT,
                           auth_status=AuthStatus.AUTHORIZED,
                           created_at=datetime(2022, 8, 4, 0, 0, 3))
            mj4.set_participants_info(participants_info)
            w5 = Workflow(name='w5', uuid='u5', state=WorkflowState.COMPLETED, target_state=None)
            mj5 = ModelJob(id=123,
                           project_id=1,
                           name='mj5',
                           workflow_uuid=w5.uuid,
                           role=ModelJobRole.COORDINATOR,
                           auth_status=AuthStatus.PENDING,
                           created_at=datetime(2022, 8, 4, 0, 0, 4))
            mj5.set_participants_info(participants_info)
            mj6 = ModelJob(id=124,
                           project_id=2,
                           name='mj6',
                           workflow_uuid=w5.uuid,
                           role=ModelJobRole.COORDINATOR,
                           auth_status=AuthStatus.PENDING,
                           created_at=datetime(2022, 8, 4, 0, 0, 4))
            mj5.set_participants_info(participants_info)
            model = Model(id=12, name='test', model_job_id=123, group_id=1, uuid='model-uuid', project_id=1)
            session.add_all([w1, w2, w3, mj1, mj2, mj3, w4, mj4, w5, mj5, mj6, model, participant, pro_participant])
            session.commit()

    def test_get_model_jobs_by_project_or_group(self):
        resp = self.get_helper('/api/v2/projects/2/model_jobs')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        model_job_names = sorted([d['name'] for d in data])
        self.assertEqual(model_job_names, ['mj6'])
        resp = self.get_helper('/api/v2/projects/1/model_jobs?group_id=2')
        data = self.get_response_data(resp)
        model_job_names = sorted([d['name'] for d in data])
        self.assertEqual(model_job_names, ['mj2'])

    def test_get_model_jobs_by_type(self):
        resp = self.get_helper('/api/v2/projects/1/model_jobs?types=TRAINING&types=EVALUATION')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        model_job_names = sorted([d['name'] for d in data])
        self.assertEqual(model_job_names, ['mj1', 'mj2'])

    def test_get_model_jobs_by_algorithm_types(self):
        resp = self.get_helper(
            '/api/v2/projects/1/model_jobs?algorithm_types=NN_VERTICAL&&algorithm_types=TREE_VERTICAL')
        data = self.get_response_data(resp)
        model_job_names = sorted([d['name'] for d in data])
        self.assertEqual(model_job_names, ['mj1', 'mj2', 'mj31'])
        resp = self.get_helper('/api/v2/projects/1/model_jobs?algorithm_types=NN_HORIZONTAL')
        data = self.get_response_data(resp)
        model_job_names = sorted([d['name'] for d in data])
        self.assertEqual(model_job_names, ['mj3'])

    def test_get_model_jobs_by_states(self):
        resp = self.get_helper('/api/v2/projects/1/model_jobs?states=PENDING_ACCEPT')
        data = self.get_response_data(resp)
        model_job_names = sorted([d['name'] for d in data])
        self.assertEqual(model_job_names, ['mj1'])
        resp = self.get_helper('/api/v2/projects/1/model_jobs?states=RUNNING&states=READY_TO_RUN')
        data = self.get_response_data(resp)
        model_job_names = sorted([d['name'] for d in data])
        self.assertEqual(model_job_names, ['mj2', 'mj3', 'mj31'])

    def test_get_model_jobs_by_keyword(self):
        resp = self.get_helper('/api/v2/projects/1/model_jobs?keyword=mj3')
        data = self.get_response_data(resp)
        model_job_names = sorted([d['name'] for d in data])
        self.assertEqual(model_job_names, ['mj3', 'mj31'])

    def test_get_model_jobs_by_configured(self):
        resp = self.get_helper('/api/v2/projects/1/model_jobs?configured=false')
        data = self.get_response_data(resp)
        self.assertEqual(sorted([d['name'] for d in data]), ['mj1', 'mj5'])
        resp = self.get_helper('/api/v2/projects/1/model_jobs?configured=true')
        data = self.get_response_data(resp)
        self.assertEqual(sorted([d['name'] for d in data]), ['mj2', 'mj3', 'mj31'])

    def test_get_model_jobs_by_expression(self):
        filter_param = urllib.parse.quote('(algorithm_type:["NN_VERTICAL","TREE_VERTICAL"])')
        resp = self.get_helper(f'/api/v2/projects/1/model_jobs?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual(sorted([d['name'] for d in data]), ['mj1', 'mj2', 'mj31'])
        filter_param = urllib.parse.quote('(algorithm_type:["NN_HORIZONTAL"])')
        resp = self.get_helper(f'/api/v2/projects/1/model_jobs?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual(sorted(d['name'] for d in data), ['mj3'])
        filter_param = urllib.parse.quote('(role:["COORDINATOR"])')
        resp = self.get_helper(f'/api/v2/projects/1/model_jobs?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual(sorted(d['name'] for d in data), ['mj1', 'mj3', 'mj5'])
        filter_param = urllib.parse.quote('(name~="1")')
        resp = self.get_helper(f'/api/v2/projects/1/model_jobs?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual(sorted(d['name'] for d in data), ['mj1', 'mj31'])
        filter_param = urllib.parse.quote('(model_job_type:["TRAINING","EVALUATION"])')
        resp = self.get_helper(f'/api/v2/projects/1/model_jobs?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual(sorted(d['name'] for d in data), ['mj1', 'mj2'])
        filter_param = urllib.parse.quote('(status:["RUNNING"])')
        resp = self.get_helper(f'/api/v2/projects/1/model_jobs?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual(sorted(d['name'] for d in data), ['mj3', 'mj31'])
        filter_param = urllib.parse.quote('(configured=true)')
        resp = self.get_helper(f'/api/v2/projects/1/model_jobs?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual(sorted(d['name'] for d in data), ['mj2', 'mj3', 'mj31'])
        filter_param = urllib.parse.quote('(auth_status:["AUTHORIZED"])')
        resp = self.get_helper(f'/api/v2/projects/1/model_jobs?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual(sorted(d['name'] for d in data), ['mj2', 'mj31'])
        sorter_param = urllib.parse.quote('created_at asc')
        resp = self.get_helper(f'/api/v2/projects/1/model_jobs?order_by={sorter_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['mj1', 'mj2', 'mj3', 'mj31', 'mj5'])
        self.assertEqual(data[0]['status'], ModelJobStatus.PENDING.name)
        self.assertEqual(data[1]['status'], ModelJobStatus.PENDING.name)
        self.assertEqual(data[2]['status'], ModelJobStatus.RUNNING.name)
        self.assertEqual(data[3]['status'], ModelJobStatus.RUNNING.name)
        self.assertEqual(data[4]['status'], ModelJobStatus.SUCCEEDED.name)
        resp = self.get_helper(f'/api/v2/projects/1/model_jobs?page=2&page_size=2&order_by={sorter_param}')
        data = self.get_response_data(resp)
        self.assertEqual(sorted(d['name'] for d in data), ['mj3', 'mj31'])

    @patch('fedlearner_webconsole.project.services.SettingService.get_system_info')
    def test_update_auth_status_of_old_data(self, mock_get_system_info):
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='test')
        with db.session_scope() as session:
            project = Project(id=3, name='project2')
            participant = Participant(id=3, name='peer2', domain_name='fl-peer2.com')
            pro_participant = ProjectParticipant(id=2, project_id=3, participant_id=3)
            model_job6 = ModelJob(id=6, project_id=3, name='j6', participants_info=None)
            model_job7 = ModelJob(id=7, project_id=3, name='j7', participants_info=None)
            session.add_all([project, participant, pro_participant, model_job6, model_job7])
            session.commit()
        resp = self.get_helper('/api/v2/projects/3/model_jobs')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        participants_info = ParticipantsInfo(
            participants_map={
                'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                'peer2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
            })
        with db.session_scope() as session:
            model_job6 = session.query(ModelJob).get(6)
            self.assertEqual(model_job6.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(model_job6.get_participants_info(), participants_info)
            model_job7 = session.query(ModelJob).get(7)
            self.assertEqual(model_job7.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(model_job7.get_participants_info(), participants_info)

    @patch('fedlearner_webconsole.rpc.v2.system_service_client.SystemServiceClient.list_flags')
    @patch('fedlearner_webconsole.two_pc.model_job_creator.ModelJobCreator.prepare')
    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager._remote_do_two_pc')
    def test_post_train_model_job(self, mock_remote_two_pc: Mock, mock_prepare: Mock, mock_list_flags: Mock):
        mock_prepare.return_value = True, ''
        config = get_workflow_config(ModelJobType.TRAINING)
        mock_remote_two_pc.return_value = True, ''
        mock_list_flags.return_value = {'model_job_global_config_enabled': True}
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            group.role = ModelJobRole.COORDINATOR
            group.algorithm_type = AlgorithmType.TREE_VERTICAL
            group.dataset_id = 1
            group.set_config(config)
            session.commit()
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'train-job',
                                    'group_id': 1,
                                    'model_job_type': 'TRAINING',
                                    'algorithm_type': 'TREE_VERTICAL',
                                    'dataset_id': 1,
                                    'config': to_dict(config),
                                    'comment': 'comment'
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).filter_by(group_id=1, version=3).first()
            self.assertEqual(model_job.project_id, 1)
            self.assertEqual(model_job.group_id, 1)
            self.assertEqual(model_job.model_job_type, ModelJobType.TRAINING)
            self.assertEqual(model_job.algorithm_type, AlgorithmType.TREE_VERTICAL)
            self.assertEqual(model_job.dataset_id, 1)
            self.assertEqual(model_job.dataset_name(), 'dataset')
            self.assertEqual(
                model_job.workflow.get_config(),
                WorkflowDefinition(job_definitions=[
                    JobDefinition(name='train-job',
                                  job_type=JobDefinition.JobType.TREE_MODEL_TRAINING,
                                  variables=[
                                      make_variable(name='mode', typed_value='train'),
                                      make_variable(name='data_source',
                                                    typed_value='dataset-job-stage-uuid-psi-data-join-job'),
                                      make_variable(name='data_path', typed_value=''),
                                      make_variable(name='file_wildcard', typed_value='*.data'),
                                  ],
                                  yaml_template='{}')
                ]))

    @patch('fedlearner_webconsole.two_pc.model_job_creator.ModelJobCreator.prepare')
    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager._remote_do_two_pc')
    def test_post_eval_model_job(self, mock_remote_two_pc: Mock, mock_prepare: Mock):
        mock_prepare.return_value = True, ''
        config = get_workflow_config(ModelJobType.EVALUATION)
        mock_remote_two_pc.return_value = True, ''
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'eval-job',
                                    'model_job_type': 'EVALUATION',
                                    'algorithm_type': 'TREE_VERTICAL',
                                    'dataset_id': 1,
                                    'config': to_dict(config),
                                    'eval_model_job_id': 123
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).filter_by(name='eval-job').first()
            self.assertEqual(model_job.project_id, 1)
            self.assertEqual(model_job.role, ModelJobRole.COORDINATOR)
            self.assertEqual(model_job.model_job_type, ModelJobType.EVALUATION)
            self.assertEqual(model_job.algorithm_type, AlgorithmType.TREE_VERTICAL)
            self.assertEqual(model_job.model_id, 12)
            self.assertEqual(model_job.dataset_id, 1)

    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager._remote_do_two_pc')
    @patch('fedlearner_webconsole.rpc.v2.system_service_client.SystemServiceClient.list_flags')
    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.create_model_job')
    def test_post_model_jobs_with_global_config(self, mock_create_model_job, mock_list_flags, mock_remote_do_two_pc):
        mock_create_model_job.return_value = Empty()
        global_config = get_global_config()
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'eval-job',
                                    'model_job_type': 'EVALUATION',
                                    'algorithm_type': 'TREE_VERTICAL',
                                    'dataset_id': 1,
                                    'model_id': 12,
                                    'global_config': to_dict(global_config),
                                    'comment': 'comment'
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).filter_by(name='eval-job').first()
            self.assertEqual(model_job.model_job_type, ModelJobType.EVALUATION)
            self.assertEqual(model_job.algorithm_type, AlgorithmType.TREE_VERTICAL)
            self.assertEqual(model_job.dataset_id, 1)
            self.assertEqual(model_job.model_id, 12)
            self.assertEqual(model_job.group_id, 1)
            self.assertEqual(model_job.get_global_config(), get_global_config())
            self.assertEqual(model_job.comment, 'comment')
            self.assertEqual(model_job.status, ModelJobStatus.PENDING)
            self.assertEqual(model_job.creator_username, 'ada')
        mock_list_flags.return_value = {'model_job_global_config_enabled': True}
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'train-job-1',
                                    'model_job_type': 'TRAINING',
                                    'algorithm_type': 'TREE_VERTICAL',
                                    'dataset_id': 1,
                                    'group_id': 1,
                                    'global_config': to_dict(global_config),
                                    'comment': 'comment'
                                })
        # fail due to no authorization
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        participants_info = ParticipantsInfo()
        participants_info.participants_map['test'].auth_status = AuthStatus.AUTHORIZED.name
        participants_info.participants_map['peer'].auth_status = AuthStatus.PENDING.name
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            group.set_participants_info(participants_info)
            group.authorized = True
            session.commit()
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'train-job-1',
                                    'model_job_type': 'TRAINING',
                                    'algorithm_type': 'TREE_VERTICAL',
                                    'dataset_id': 1,
                                    'group_id': 1,
                                    'global_config': to_dict(global_config),
                                    'comment': 'comment'
                                })
        # fail due to peer no authorization
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            participants_info = group.get_participants_info()
            participants_info.participants_map['peer'].auth_status = AuthStatus.AUTHORIZED.name
            group.set_participants_info(participants_info)
            session.commit()
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'train-job-1',
                                    'model_job_type': 'TRAINING',
                                    'algorithm_type': 'TREE_VERTICAL',
                                    'dataset_id': 1,
                                    'group_id': 1,
                                    'global_config': to_dict(global_config),
                                    'comment': 'comment'
                                })
        # create successfully
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).filter_by(name='train-job-1').first()
            self.assertEqual(model_job.model_job_type, ModelJobType.TRAINING)
            self.assertEqual(model_job.version, 3)
        mock_list_flags.return_value = {'model_job_global_config_enabled': False}
        mock_remote_do_two_pc.return_value = True, ''
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            group.role = ModelJobRole.COORDINATOR
            group.algorithm_type = AlgorithmType.NN_VERTICAL
            group.set_config()
            session.commit()
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'train-job-2',
                                    'model_job_type': 'TRAINING',
                                    'algorithm_type': 'NN_VERTICAL',
                                    'dataset_id': 1,
                                    'group_id': 1,
                                    'global_config': to_dict(global_config),
                                    'comment': 'comment'
                                })
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).filter_by(group_id=1, version=4).first()
            self.assertIsNotNone(model_job)
            self.assertEqual(model_job.model_job_type, ModelJobType.TRAINING)
            self.assertEqual(model_job.algorithm_type, AlgorithmType.NN_VERTICAL)

    @patch('fedlearner_webconsole.rpc.v2.system_service_client.SystemServiceClient.list_flags')
    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.update_model_job_group')
    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.create_model_job')
    def test_post_auto_update_model_job(self, mock_creat_model_job: MagicMock, mock_update_model_job_group: MagicMock,
                                        mock_list_flags: MagicMock):
        mock_creat_model_job.return_value = Empty()
        mock_list_flags.return_value = {'model_job_global_config_enabled': True}
        global_config = get_global_config()
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            dataset_job.kind = DatasetJobKind.OT_PSI_DATA_JOIN
            participants_info = ParticipantsInfo()
            participants_info.participants_map['test'].auth_status = AuthStatus.AUTHORIZED.name
            participants_info.participants_map['peer'].auth_status = AuthStatus.AUTHORIZED.name
            group = session.query(ModelJobGroup).get(1)
            group.set_participants_info(participants_info)
            group.authorized = True
            session.commit()
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'auto-update-train-job-1',
                                    'model_job_type': 'TRAINING',
                                    'algorithm_type': 'NN_VERTICAL',
                                    'dataset_id': 1,
                                    'data_batch_id': 1,
                                    'group_id': 1,
                                    'global_config': to_dict(global_config),
                                    'comment': 'comment'
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        self.assertEqual(mock_update_model_job_group.call_args_list, [
            call(auto_update_status=GroupAutoUpdateStatus.ACTIVE,
                 start_dataset_job_stage_uuid='dataset-job-stage-uuid',
                 uuid='uuid')
        ])
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).filter_by(group_id=1, version=3).first()
            self.assertIsNotNone(model_job)
            self.assertEqual(model_job.model_job_type, ModelJobType.TRAINING)
            self.assertEqual(model_job.algorithm_type, AlgorithmType.NN_VERTICAL)
            self.assertEqual(model_job.auto_update, True)
            self.assertEqual(model_job.data_batch_id, 1)
            group: ModelJobGroup = session.query(ModelJobGroup).get(1)
            self.assertEqual(group.start_data_batch_id, 1)
            self.assertEqual(group.auto_update_status, GroupAutoUpdateStatus.ACTIVE)

    def test_post_model_jobs_failed(self):
        # fail due to missing model_id for eval job
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'eval-job',
                                    'model_job_type': 'EVALUATION',
                                    'algorithm_type': 'TREE_VERTICAL',
                                    'dataset_id': 1,
                                    'config': {},
                                })
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        # fail due to model_id existence for train job
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'train-job',
                                    'model_job_type': 'TRAINING',
                                    'algorithm_type': 'TREE_VERTICAL',
                                    'dataset_id': 1,
                                    'config': {},
                                    'model_id': 1
                                })
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

    def test_post_horizontal_eval_model_job(self):
        with db.session_scope() as session:
            model = Model(id=1, name='train-model', project_id=1)
            session.add(model)
            session.commit()
        config = get_workflow_config(ModelJobType.EVALUATION)
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'eval-job',
                                    'model_job_type': 'EVALUATION',
                                    'algorithm_type': 'NN_HORIZONTAL',
                                    'algorithm_id': 3,
                                    'model_id': 1,
                                    'config': to_dict(config),
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(name='eval-job').first()
            self.assertEqual(model_job.project_id, 1)
            self.assertEqual(model_job.algorithm_type, AlgorithmType.NN_HORIZONTAL)
            self.assertEqual(model_job.role, ModelJobRole.COORDINATOR)
            self.assertEqual(model_job.algorithm_id, 3)
            self.assertEqual(model_job.model_id, 1)
            self.assertEqual(model_job.model_job_type, ModelJobType.EVALUATION)

    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager._remote_do_two_pc')
    def test_post_model_job_failed_due_to_dataset(self, mock_remote_two_pc):
        config = get_workflow_config(ModelJobType.EVALUATION)
        mock_remote_two_pc.return_value = True, ''
        # failed due to dataset is not found
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'eval-job',
                                    'model_job_type': 'EVALUATION',
                                    'algorithm_type': 'TREE_VERTICAL',
                                    'dataset_id': 3,
                                    'config': to_dict(config),
                                    'eval_model_job_id': 123
                                })
        self.assertEqual(resp.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(1)
            dataset.is_published = False
            session.add(dataset)
            session.commit()
        resp = self.post_helper('/api/v2/projects/1/model_jobs',
                                data={
                                    'name': 'eval-job',
                                    'model_job_type': 'EVALUATION',
                                    'algorithm_type': 'TREE_VERTICAL',
                                    'dataset_id': 2,
                                    'config': to_dict(config),
                                    'eval_model_job_id': 123
                                })
        self.assertEqual(resp.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)


class ModelJobApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        Envs.SYSTEM_INFO = '{"domain_name": "fl-test.com"}'
        with db.session_scope() as session:
            project = Project(id=1, name='test-project')
            participant = Participant(id=1, name='part', domain_name='fl-demo1.com')
            pro_part = ProjectParticipant(id=1, project_id=1, participant_id=1)
            group = ModelJobGroup(id=1, name='test-group', project_id=project.id, uuid='uuid')
            workflow_uuid = 'uuid'
            workflow = Workflow(id=1,
                                name='test-workflow-1',
                                project_id=1,
                                state=WorkflowState.NEW,
                                target_state=WorkflowState.READY,
                                transaction_state=TransactionState.PARTICIPANT_PREPARE,
                                uuid=workflow_uuid)
            dataset_job = DatasetJob(id=1,
                                     name='datasetjob',
                                     uuid='uuid',
                                     state=DatasetJobState.SUCCEEDED,
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=3,
                                     kind=DatasetJobKind.OT_PSI_DATA_JOIN)
            dataset = Dataset(id=3,
                              uuid='uuid',
                              name='dataset',
                              dataset_type=DatasetType.PSI,
                              path='/data/dataset/haha')
            model_job = ModelJob(id=1,
                                 name='test-model-job',
                                 group_id=1,
                                 project_id=1,
                                 dataset_id=3,
                                 model_job_type=ModelJobType.TRAINING,
                                 algorithm_type=AlgorithmType.TREE_VERTICAL,
                                 workflow_id=1,
                                 workflow_uuid=workflow_uuid,
                                 job_id=2,
                                 job_name='uuid-train-job',
                                 created_at=datetime(2022, 5, 10, 0, 0, 0))
            participants_info = ParticipantsInfo(
                participants_map={
                    'test': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                    'demo1': ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                })
            model_job.set_participants_info(participants_info)
            session.add_all([project, group, workflow, model_job, dataset, dataset_job, participant, pro_part])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.get_model_job')
    def test_get_model_job(self, mock_get_model_job):
        mock_get_model_job.side_effect = [ModelJobPb(auth_status=AuthStatus.AUTHORIZED.name)]
        with db.session_scope() as session:
            workflow: Workflow = session.query(Workflow).filter_by(uuid='uuid').first()
            config = get_workflow_config(model_job_type=ModelJobType.TRAINING)
            workflow.set_config(config)
            workflow.state = WorkflowState.READY
            workflow.target_state = None
            workflow.start_at = 1
            workflow.stop_at = 2
            model_job: ModelJob = session.query(ModelJob).get(1)
            model = Model(id=1,
                          name='test-model',
                          model_job_id=model_job.id,
                          group_id=model_job.group_id,
                          created_at=datetime(2022, 5, 10, 0, 0, 0),
                          updated_at=datetime(2022, 5, 10, 0, 0, 0))
            session.add(model)
            session.commit()
        resp = self.get_helper('/api/v2/projects/1/model_jobs/1')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.maxDiff = None
        self.assertPartiallyEqual(data, {
            'id': 1,
            'name': 'test-model-job',
            'role': 'PARTICIPANT',
            'model_job_type': 'TRAINING',
            'algorithm_type': 'TREE_VERTICAL',
            'auth_status': 'PENDING',
            'auto_update': False,
            'status': 'PENDING',
            'error_message': '',
            'group_id': 1,
            'project_id': 1,
            'state': 'READY_TO_RUN',
            'configured': True,
            'dataset_id': 3,
            'dataset_name': 'dataset',
            'output_model_name': 'test-model',
            'created_at': 1652140800,
            'started_at': 1,
            'stopped_at': 2,
            'uuid': '',
            'algorithm_id': 0,
            'model_id': 0,
            'model_name': '',
            'workflow_id': 1,
            'job_id': 2,
            'job_name': 'uuid-train-job',
            'creator_username': '',
            'coordinator_id': 0,
            'comment': '',
            'version': 0,
            'metric_is_public': False,
            'auth_frontend_status': 'SELF_AUTH_PENDING',
            'participants_info': {
                'participants_map': {
                    'demo1': {
                        'auth_status': 'AUTHORIZED',
                        'name': '',
                        'role': '',
                        'state': '',
                        'type': ''
                    },
                    'test': {
                        'auth_status': 'PENDING',
                        'name': '',
                        'role': '',
                        'state': '',
                        'type': ''
                    }
                }
            }
        },
                                  ignore_fields=['config', 'output_models', 'updated_at', 'data_batch_id'])

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.inform_model_job')
    @patch('fedlearner_webconsole.project.services.SettingService.get_system_info')
    @patch('fedlearner_webconsole.scheduler.scheduler.Scheduler.wakeup')
    def test_put_model_job(self, mock_wake_up, mock_get_system_info, mock_inform_model_job):
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='test')
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            model_job.uuid = 'uuid'
            session.commit()
        config = get_workflow_config(ModelJobType.TRAINING)
        data = {'algorithm_id': 1, 'config': to_dict(config)}
        resp = self.put_helper('/api/v2/projects/1/model_jobs/1', data=data)
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(data['configured'], True)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            self.assertEqual(model_job.role, ModelJobRole.PARTICIPANT)
            workflow = session.query(Workflow).filter_by(uuid='uuid').first()
            self.assertEqual(workflow.template.name, 'sys-preset-tree-model')
            self.assertEqual(
                workflow.get_config(),
                WorkflowDefinition(job_definitions=[
                    JobDefinition(name='train-job',
                                  job_type=JobDefinition.JobType.TREE_MODEL_TRAINING,
                                  variables=[
                                      make_variable(name='mode', typed_value='train'),
                                      make_variable(name='data_source', typed_value=''),
                                      make_variable(name='data_path', typed_value='/data/dataset/haha/batch'),
                                      make_variable(name='file_wildcard', typed_value='**/part*')
                                  ],
                                  yaml_template='{}')
                ]))
            participants_info = ParticipantsInfo(
                participants_map={
                    'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'demo1': ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                })
            self.assertEqual(model_job.get_participants_info(), participants_info)
            self.assertEqual(mock_inform_model_job.call_args_list, [(('uuid', AuthStatus.AUTHORIZED),)])
            mock_wake_up.assert_called_with(model_job.workflow_id)

    @patch('fedlearner_webconsole.project.services.SettingService.get_system_info')
    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.inform_model_job')
    def test_patch_model_job(self, mock_inform_model_job, mock_get_system_info):
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='test')
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            model_job.uuid = 'uuid'
            participants_info = ParticipantsInfo(
                participants_map={
                    'test': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                    'demo1': ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                })
            model_job.set_participants_info(participants_info)
            session.commit()
        resp = self.patch_helper('/api/v2/projects/1/model_jobs/1',
                                 data={
                                     'metric_is_public': False,
                                     'auth_status': 'HAHA'
                                 })
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        resp = self.patch_helper('/api/v2/projects/1/model_jobs/1',
                                 data={
                                     'metric_is_public': False,
                                     'auth_status': 'PENDING',
                                     'comment': 'hahahaha'
                                 })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            self.assertFalse(model_job.metric_is_public)
            self.assertEqual(model_job.auth_status, AuthStatus.PENDING)
            participants_info = ParticipantsInfo(
                participants_map={
                    'test': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                    'demo1': ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                })
            self.assertEqual(model_job.get_participants_info(), participants_info)
            self.assertEqual(mock_inform_model_job.call_args_list, [(('uuid', AuthStatus.PENDING),)])
            self.assertEqual(model_job.creator_username, 'ada')
            self.assertEqual(model_job.comment, 'hahahaha')
        mock_inform_model_job.reset_mock()
        self.patch_helper('/api/v2/projects/1/model_jobs/1',
                          data={
                              'metric_is_public': True,
                              'auth_status': 'AUTHORIZED'
                          })
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            self.assertTrue(model_job.metric_is_public)
            self.assertEqual(model_job.auth_status, AuthStatus.AUTHORIZED)
            participants_info = ParticipantsInfo(
                participants_map={
                    'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'demo1': ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                })
            self.assertEqual(model_job.get_participants_info(), participants_info)
            self.assertEqual(mock_inform_model_job.call_args_list, [(('uuid', AuthStatus.AUTHORIZED),)])

    @patch('fedlearner_webconsole.mmgr.model_job_configer.ModelJobConfiger.get_config')
    def test_put_model_job_with_global_config(self, mock_get_config):
        mock_get_config.return_value = get_workflow_config(ModelJobType.TRAINING)
        global_config = get_global_config()
        resp = self.put_helper('/api/v2/projects/1/model_jobs/1',
                               data={
                                   'dataset_id': 3,
                                   'global_config': to_dict(global_config),
                               })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        mock_get_config.assert_called_with(dataset_id=3,
                                           model_id=None,
                                           model_job_config=global_config.global_config['test'])
        with db.session_scope() as sesssion:
            self.maxDiff = None
            model_job: ModelJob = sesssion.query(ModelJob).get(1)
            self.assertEqual(model_job.dataset_id, 3)
            self.assertEqual(
                model_job.config(),
                WorkflowDefinition(job_definitions=[
                    JobDefinition(name='train-job',
                                  job_type=JobDefinition.JobType.TREE_MODEL_TRAINING,
                                  variables=[
                                      make_variable('mode', typed_value='train'),
                                      make_variable('data_source', typed_value=''),
                                      make_variable('data_path', typed_value='/data/dataset/haha/batch'),
                                      make_variable('file_wildcard', typed_value='**/part*')
                                  ],
                                  yaml_template='{}')
                ]))

    def test_delete_model_job(self):
        resp = self.delete_helper('/api/v2/projects/1/model_jobs/1')
        self.assertEqual(resp.status_code, HTTPStatus.CONFLICT)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            model_job.workflow.state = WorkflowState.STOPPED
            session.commit()
        resp = self.delete_helper('/api/v2/projects/1/model_jobs/1')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).execution_options(include_deleted=True).get(1)
            self.assertIsNotNone(model_job.deleted_at)


class ModelJobResultsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=123, name='test-project')
            session.add(project)
            model_job = ModelJob(id=123, name='test-model', project_id=project.id, job_name='test-job')
            session.add(model_job)
            session.commit()

    @patch('fedlearner_webconsole.mmgr.models.ModelJob.get_job_path')
    def test_get_results(self, mock_get_job_path):
        with tempfile.TemporaryDirectory() as file:
            mock_get_job_path.return_value = file
            Path(os.path.join(file, 'outputs')).mkdir()
            Path(os.path.join(file, 'outputs', '1.output')).write_text('output_1', encoding='utf-8')
            Path(os.path.join(file, 'outputs', '2.output')).write_text('output_2', encoding='utf-8')
            resp = self.get_helper('/api/v2/projects/123/model_jobs/123/results')
            self.assertEqual(resp.status_code, HTTPStatus.OK)
            self.assertEqual(resp.content_type, 'application/x-tar')
            with tarfile.TarFile(fileobj=BytesIO(resp.data)) as tar:
                with tempfile.TemporaryDirectory() as temp_dir:
                    tar.extractall(temp_dir)
                    self.assertEqual(['1.output', '2.output'], sorted(os.listdir(os.path.join(temp_dir, 'outputs'))))
                    with open(os.path.join(temp_dir, 'outputs', '1.output'), encoding='utf-8') as f:
                        self.assertEqual(f.read(), 'output_1')


class StartModelJobApiTest(BaseTestCase):

    @patch('fedlearner_webconsole.mmgr.model_job_apis.start_model_job')
    def test_start_model_job(self, mock_start_model_job: MagicMock):
        with db.session_scope() as session:
            model_job = ModelJob(id=1, name='train-job', project_id=1)
            session.add(model_job)
            session.commit()
        resp = self.post_helper(f'/api/v2/projects/1/model_jobs/{model_job.id}:start')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        mock_start_model_job.assert_called_with(model_job_id=1)


class StopModelJobApiTest(BaseTestCase):

    @patch('fedlearner_webconsole.mmgr.model_job_apis.stop_model_job')
    def test_stop_model_job(self, mock_stop_model_job: MagicMock):
        with db.session_scope() as session:
            model_job = ModelJob(id=1, name='train_job', workflow_id=1, project_id=1)
            session.add(model_job)
            session.commit()
        resp = self.post_helper(f'/api/v2/projects/1/model_jobs/{model_job.id}:stop')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        mock_stop_model_job.assert_called_with(model_job_id=1)


class PeerModelJobTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        project = Project(id=1, name='project')
        participant = Participant(id=1, name='party', domain_name='fl-test.com', host='127.0.0.1', port=32443)
        relationship = ProjectParticipant(project_id=1, participant_id=1)
        model_job = ModelJob(id=1, project_id=1, name='model-job', uuid='uuid', workflow_uuid='workflow_uuid')
        workflow = Workflow(name='workflow', uuid='workflow_uuid')
        workflow.set_config(WorkflowDefinition(group_alias='haha'))
        with db.session_scope() as session:
            session.add_all([project, participant, relationship, model_job])
            session.commit()

    @patch('fedlearner_webconsole.rpc.client.RpcClient.get_model_job')
    def test_get_peer_model_job(self, mock_get_model_job):
        mock_get_model_job.return_value = GetModelJobResponse(name='name',
                                                              uuid='uuid',
                                                              group_uuid='uuid',
                                                              algorithm_type='NN_VERTICAL',
                                                              model_job_type='TRAINING',
                                                              state='COMPLETED',
                                                              metrics='12',
                                                              metric_is_public=BoolValue(value=False))
        resp = self.get_helper('/api/v2/projects/1/model_jobs/1/peers/1')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        mock_get_model_job.assert_called_with(model_job_uuid='uuid', need_metrics=False)
        self.assertResponseDataEqual(
            resp, {
                'name': 'name',
                'uuid': 'uuid',
                'algorithm_type': 'NN_VERTICAL',
                'model_job_type': 'TRAINING',
                'group_uuid': 'uuid',
                'state': 'COMPLETED',
                'config': {
                    'group_alias': '',
                    'variables': [],
                    'job_definitions': []
                },
                'metric_is_public': False,
            })


class PeerModelJobMetricsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        project = Project(id=1, name='project')
        participant = Participant(id=1, name='party', domain_name='fl-test.com', host='127.0.0.1', port=32443)
        relationship = ProjectParticipant(project_id=1, participant_id=1)
        model_job = ModelJob(id=1, project_id=1, name='model-job', uuid='uuid', workflow_uuid='workflow_uuid')
        with db.session_scope() as session:
            session.add_all([project, participant, relationship, model_job])
            session.commit()

    @patch('fedlearner_webconsole.rpc.client.RpcClient.get_model_job')
    def test_get_peer_model_job(self, mock_get_model_job):
        metrics = {'auc': 0.5}
        mock_get_model_job.return_value = GetModelJobResponse(name='name', uuid='uuid', metrics=json.dumps(metrics))
        resp = self.get_helper('/api/v2/projects/1/model_jobs/1/peers/1/metrics')
        mock_get_model_job.assert_called_with(model_job_uuid='uuid', need_metrics=True)
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {'auc': 0.5})
        mock_get_model_job.assert_called_with(model_job_uuid='uuid', need_metrics=True)
        self.assertEqual(self.get_response_data(resp), metrics)
        mock_get_model_job.return_value = GetModelJobResponse(name='name',
                                                              uuid='uuid',
                                                              metric_is_public=BoolValue(value=False))
        resp = self.get_helper('/api/v2/projects/1/model_jobs/1/peers/1/metrics')
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)
        mock_get_model_job.return_value = GetModelJobResponse(name='name',
                                                              uuid='uuid',
                                                              metric_is_public=BoolValue(value=True))
        resp = self.get_helper('/api/v2/projects/1/model_jobs/1/peers/1/metrics')
        # internal error since the metric is not valid
        self.assertEqual(resp.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)


class LaunchModelJobApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            _insert_or_update_templates(session)
            project = Project(id=1, name='test-project')
            dataset_job = DatasetJob(id=1,
                                     name='datasetjob',
                                     uuid='uuid',
                                     state=DatasetJobState.SUCCEEDED,
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=3,
                                     kind=DatasetJobKind.OT_PSI_DATA_JOIN)
            dataset = Dataset(id=3,
                              uuid='uuid',
                              name='datasetjob',
                              dataset_type=DatasetType.PSI,
                              path='/data/dataset/haha')
            algorithm = Algorithm(id=2, name='algorithm')
            group = ModelJobGroup(name='group',
                                  uuid='uuid',
                                  project_id=1,
                                  algorithm_type=AlgorithmType.NN_VERTICAL,
                                  algorithm_id=2,
                                  role=ModelJobRole.COORDINATOR,
                                  dataset_id=3)
            group.set_config(get_workflow_config(ModelJobType.TRAINING))
            session.add_all([dataset_job, dataset, project, group, algorithm])
            session.commit()

    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager._remote_do_two_pc')
    def test_launch_model_job(self, mock_remote_do_two_pc):
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).filter_by(uuid='uuid').first()
        mock_remote_do_two_pc.return_value = True, ''
        resp = self.post_helper(f'/api/v2/projects/1/model_job_groups/{group.id}:launch')
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).filter_by(name='group').first()
            model_job = group.model_jobs[0]
            self.assertEqual(model_job.group_id, group.id)
            self.assertTrue(model_job.project_id, group.project_id)
            self.assertEqual(model_job.version, 1)
            self.assertEqual(group.latest_version, 1)
            self.assertTrue(model_job.algorithm_type, group.algorithm_type)
            self.assertTrue(model_job.model_job_type, ModelJobType.TRAINING)
            self.assertTrue(model_job.dataset_id, group.dataset_id)
            self.assertTrue(model_job.workflow.get_config(), group.get_config())


class NextAutoUpdateModelJobApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            data_batch = DataBatch(id=1,
                                   name='20220101-08',
                                   dataset_id=1,
                                   event_time=datetime(year=2000, month=1, day=1, hour=8),
                                   latest_parent_dataset_job_stage_id=1)
            group1 = ModelJobGroup(id=1, name='group1', project_id=1, auto_update_status=GroupAutoUpdateStatus.ACTIVE)
            group2 = ModelJobGroup(id=2, name='group2', project_id=1, auto_update_status=GroupAutoUpdateStatus.ACTIVE)
            group3 = ModelJobGroup(id=3, name='group3', project_id=1, auto_update_status=GroupAutoUpdateStatus.ACTIVE)
            model_job1 = ModelJob(id=1,
                                  group_id=1,
                                  auto_update=False,
                                  project_id=1,
                                  created_at=datetime(2022, 12, 16, 1, 0, 0),
                                  status=ModelJobStatus.SUCCEEDED,
                                  data_batch_id=1)
            global_config2 = ModelJobGlobalConfig(
                dataset_uuid='uuid',
                global_config={
                    'test1': ModelJobConfig(algorithm_uuid='uuid1', variables=[Variable(name='load_model_name')]),
                    'test2': ModelJobConfig(algorithm_uuid='uuid2', variables=[Variable(name='load_model_name')])
                })
            model_job2 = ModelJob(id=2,
                                  group_id=2,
                                  auto_update=True,
                                  project_id=1,
                                  data_batch_id=5,
                                  created_at=datetime(2022, 12, 16, 2, 0, 0),
                                  status=ModelJobStatus.RUNNING)
            model_job2.set_global_config(global_config2)
            global_config3 = ModelJobGlobalConfig(
                dataset_uuid='uuid',
                global_config={
                    'test1': ModelJobConfig(algorithm_uuid='uuid1', variables=[Variable(name='load_model_name')]),
                    'test2': ModelJobConfig(algorithm_uuid='uuid2', variables=[Variable(name='load_model_name')])
                })
            model_job3 = ModelJob(id=3,
                                  name='test-model',
                                  group_id=3,
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
            model_job3.set_global_config(global_config3)
            session.add_all([project, group1, group2, group3, model_job1, model_job2, model_job3, data_batch])
            session.commit()

    @patch('fedlearner_webconsole.dataset.services.BatchService.get_next_batch')
    def test_get_next_auto_update_model_job(self, mock_get_next_batch: MagicMock):
        # fail due to model job group has no auto update model jobs
        resp = self.get_helper('/api/v2/projects/1/model_job_groups/1/next_auto_update_model_job')
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)
        # fail due to the latest auto update model job is running
        mock_get_next_batch.return_value = DataBatch(id=2)
        resp = self.get_helper('/api/v2/projects/1/model_job_groups/2/next_auto_update_model_job')
        self.assertEqual(resp.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(2)
            model_job.status = ModelJobStatus.CONFIGURED
            session.commit()
        resp = self.get_helper('/api/v2/projects/1/model_job_groups/2/next_auto_update_model_job')
        self.assertEqual(resp.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(2)
            model_job.status = ModelJobStatus.PENDING
            session.commit()
        resp = self.get_helper('/api/v2/projects/1/model_job_groups/2/next_auto_update_model_job')
        self.assertEqual(resp.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        # when the latest auto update model job is stopped and there is no previous successful model job
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(2)
            model_job.status = ModelJobStatus.STOPPED
            session.commit()
        resp = self.get_helper('/api/v2/projects/1/model_job_groups/2/next_auto_update_model_job')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(data['data_batch_id'], 5)
        global_config = ModelJobGlobalConfig(dataset_uuid='uuid',
                                             global_config={
                                                 'test1':
                                                     ModelJobConfig(algorithm_uuid='uuid1',
                                                                    variables=[
                                                                        Variable(name='load_model_name',
                                                                                 value='',
                                                                                 value_type=Variable.ValueType.STRING)
                                                                    ]),
                                                 'test2':
                                                     ModelJobConfig(algorithm_uuid='uuid2',
                                                                    variables=[
                                                                        Variable(name='load_model_name',
                                                                                 value='',
                                                                                 value_type=Variable.ValueType.STRING)
                                                                    ])
                                             })
        self.assertEqual(data['global_config'], to_dict(global_config))
        # when the latest auto model job is failed and there is previous successful auto update model job
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(2)
            model_job.status = ModelJobStatus.FAILED
            global_config = ModelJobGlobalConfig(
                dataset_uuid='uuid',
                global_config={
                    'test1': ModelJobConfig(algorithm_uuid='uuid1', variables=[Variable(name='load_model_name')]),
                    'test2': ModelJobConfig(algorithm_uuid='uuid2', variables=[Variable(name='load_model_name')])
                })
            model_job = ModelJob(id=4,
                                 group_id=2,
                                 auto_update=True,
                                 project_id=1,
                                 data_batch_id=3,
                                 created_at=datetime(2022, 12, 16, 1, 0, 0),
                                 status=ModelJobStatus.SUCCEEDED,
                                 model_id=2)
            model = Model(id=2, model_job_id=4, name='test-previous-model')
            model_job.set_global_config(global_config)
            session.add_all([model, model_job])
            session.commit()
        mock_get_next_batch.return_value = DataBatch(id=4)
        resp = self.get_helper('/api/v2/projects/1/model_job_groups/2/next_auto_update_model_job')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(data['data_batch_id'], 4)
        global_config = ModelJobGlobalConfig(
            dataset_uuid='uuid',
            global_config={
                'test1':
                    ModelJobConfig(algorithm_uuid='uuid1',
                                   variables=[
                                       Variable(name='load_model_name',
                                                value='test-previous-model',
                                                typed_value=Value(string_value='test-previous-model'),
                                                value_type=Variable.ValueType.STRING)
                                   ]),
                'test2':
                    ModelJobConfig(algorithm_uuid='uuid2',
                                   variables=[
                                       Variable(name='load_model_name',
                                                value='test-previous-model',
                                                typed_value=Value(string_value='test-previous-model'),
                                                value_type=Variable.ValueType.STRING)
                                   ])
            })
        self.assertEqual(data['global_config'], to_dict(global_config))
        # when the latest auto update model job is succeeded and next batch is None
        mock_get_next_batch.return_value = None
        resp = self.get_helper('/api/v2/projects/1/model_job_groups/3/next_auto_update_model_job')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(data['data_batch_id'], 0)
        global_config = ModelJobGlobalConfig(dataset_uuid='uuid',
                                             global_config={
                                                 'test1':
                                                     ModelJobConfig(algorithm_uuid='uuid1',
                                                                    variables=[
                                                                        Variable(name='load_model_name',
                                                                                 value='',
                                                                                 typed_value=Value(string_value=''),
                                                                                 value_type=Variable.ValueType.STRING)
                                                                    ]),
                                                 'test2':
                                                     ModelJobConfig(algorithm_uuid='uuid2',
                                                                    variables=[
                                                                        Variable(name='load_model_name',
                                                                                 value='',
                                                                                 typed_value=Value(string_value=''),
                                                                                 value_type=Variable.ValueType.STRING)
                                                                    ])
                                             })
        self.assertEqual(data['global_config'], to_dict(global_config))
        # when the latest auto update model job is succeeded and there is next data batch, but there is no model
        mock_get_next_batch.return_value = DataBatch(id=3)
        resp = self.get_helper('/api/v2/projects/1/model_job_groups/3/next_auto_update_model_job')
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)
        # when the latest auto update model job is succeeded and there is next data batch, and there is model
        with db.session_scope() as session:
            model = Model(id=1, name='test-model', model_job_id=3, uuid='uuid')
            session.add(model)
            session.commit()
        mock_get_next_batch.return_value = DataBatch(id=3)
        resp = self.get_helper('/api/v2/projects/1/model_job_groups/3/next_auto_update_model_job')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        global_config = ModelJobGlobalConfig(
            dataset_uuid='uuid',
            global_config={
                'test1':
                    ModelJobConfig(algorithm_uuid='uuid1',
                                   variables=[
                                       Variable(name='load_model_name',
                                                value='test-model',
                                                typed_value=Value(string_value='test-model'),
                                                value_type=Variable.ValueType.STRING)
                                   ]),
                'test2':
                    ModelJobConfig(algorithm_uuid='uuid2',
                                   variables=[
                                       Variable(name='load_model_name',
                                                value='test-model',
                                                typed_value=Value(string_value='test-model'),
                                                value_type=Variable.ValueType.STRING)
                                   ])
            })
        self.assertEqual(data['data_batch_id'], 3)
        self.assertEqual(data['global_config'], to_dict(global_config))
        self.assertEqual(data['model_id'], 1)


class ModelJobDefinitionApiTest(BaseTestCase):

    def test_get_definitions(self):
        resp = self.get_helper('/api/v2/model_job_definitions?algorithm_type=NN_VERTICAL&model_job_type=TRAINING')
        data = self.get_response_data(resp)
        self.assertEqual(data['is_federated'], True)
        self.assertEqual(len(data['variables']), 32)
        resp = self.get_helper('/api/v2/model_job_definitions?algorithm_type=NN_HORIZONTAL&model_job_type=EVALUATION')
        data = self.get_response_data(resp)
        self.assertEqual(data['is_federated'], False)
        self.assertEqual(len(data['variables']), 8)


if __name__ == '__main__':
    unittest.main()

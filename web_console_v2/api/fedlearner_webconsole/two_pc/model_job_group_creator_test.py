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
from unittest.mock import Mock, patch

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import Dataset, ResourceState
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.two_pc.model_job_group_creator import ModelJobGroupCreator
from fedlearner_webconsole.mmgr.models import ModelJobGroup, GroupCreateStatus
from fedlearner_webconsole.proto.two_pc_pb2 import CreateModelJobGroupData, \
    TransactionData
from fedlearner_webconsole.proto.project_pb2 import ParticipantInfo, ParticipantsInfo
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus


class ModelJobGroupCreatorTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        project = Project(id=1, name='project')
        participant = Participant(id=123, name='party', domain_name='fl-demo.com')
        relationship = ProjectParticipant(project_id=1, participant_id=123)
        dataset = Dataset(name='dataset', uuid='dataset_uuid', is_published=True)
        with db.session_scope() as session:
            session.add_all([project, participant, dataset, relationship])
            session.commit()

    @staticmethod
    def get_transaction_data(group_name: str, group_uuid: str, project_name: str, dataset_uuid: str):
        return TransactionData(
            create_model_job_group_data=CreateModelJobGroupData(model_job_group_name=group_name,
                                                                model_job_group_uuid=group_uuid,
                                                                project_name=project_name,
                                                                algorithm_type=AlgorithmType.NN_VERTICAL.name,
                                                                coordinator_pure_domain_name='demo',
                                                                dataset_uuid=dataset_uuid))

    @patch('fedlearner_webconsole.dataset.models.Dataset.get_frontend_state')
    def test_prepare(self, mock_get_frontend_state: Mock):
        mock_get_frontend_state.return_value = ResourceState.SUCCEEDED
        data = self.get_transaction_data('group', 'uuid', 'project', 'dataset_uuid')
        with db.session_scope() as session:
            creator = ModelJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertTrue(flag)
        with db.session_scope() as session:
            model_job_group = ModelJobGroup(name='group', uuid='uuid')
            session.add(model_job_group)
            session.commit()
        # test for idempotence for creating group with same name and uuid
        with db.session_scope() as session:
            creator = ModelJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertTrue(flag)
        # fail due to uuid not consistent
        data = self.get_transaction_data('group', 'uuid-1', 'project', 'dataset_uuid')
        with db.session_scope() as session:
            creator = ModelJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertFalse(flag)
            self.assertEqual(msg, 'model group group with different uuid already exist')
        # fail due to project not found
        data = self.get_transaction_data('group', 'uuid', 'project-1', 'dataset_uuid')
        with db.session_scope() as session:
            creator = ModelJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertFalse(flag)
            self.assertEqual(msg, 'project group not exists')
        # fail due to dataset not found
        data = self.get_transaction_data('group', 'uuid', 'project', 'dataset_uuid-1')
        with db.session_scope() as session:
            creator = ModelJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertFalse(flag)
            self.assertEqual(msg, 'dataset dataset_uuid-1 not exists')
        # fail due to dataset is not published
        with db.session_scope() as session:
            dataset = session.query(Dataset).filter_by(uuid='dataset_uuid').first()
            dataset.is_published = False
            session.add(dataset)
            session.commit()
        data = self.get_transaction_data('group', 'uuid', 'project', 'dataset_uuid')
        with db.session_scope() as session:
            creator = ModelJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertFalse(flag)
            self.assertEqual(msg, 'dataset dataset_uuid is not published')
        # fail due to dataset is not succeeded
        mock_get_frontend_state.return_value = ResourceState.PROCESSING
        with db.session_scope() as session:
            creator = ModelJobGroupCreator(session, '12', data)
            flag, msg = creator.prepare()
            self.assertFalse(flag)
            self.assertEqual(msg, 'dataset dataset_uuid is not succeeded')

    @patch('fedlearner_webconsole.setting.service.get_pure_domain_name')
    def test_commit(self, mock_pure_domain_name: Mock):
        mock_pure_domain_name.return_value = 'test'
        data = self.get_transaction_data('group', 'uuid', 'project', 'dataset_uuid')
        with db.session_scope() as session:
            creator = ModelJobGroupCreator(session, '12', data)
            flag, msg = creator.commit()
            session.commit()
            self.assertTrue(flag)
        with db.session_scope() as session:
            model_job_group = session.query(ModelJobGroup).filter_by(name='group').first()
            project = session.query(Project).filter_by(name='project').first()
            dataset = session.query(Dataset).filter_by(uuid='dataset_uuid').first()
            self.assertEqual(model_job_group.uuid, 'uuid')
            self.assertEqual(model_job_group.project_id, project.id)
            self.assertEqual(model_job_group.algorithm_type, AlgorithmType.NN_VERTICAL)
            self.assertEqual(model_job_group.coordinator_id, 123)
            self.assertEqual(model_job_group.dataset_id, dataset.id)
            self.assertEqual(
                model_job_group.get_participants_info(),
                ParticipantsInfo(
                    participants_map={
                        'test': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                        'demo': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                    }))

    def test_abort(self):
        data = self.get_transaction_data('group', 'uuid', 'project', 'dataset_uuid')
        with db.session_scope() as session:
            creator = ModelJobGroupCreator(session, '12', data)
            flag, msg = creator.abort()
            session.commit()
            self.assertTrue(flag)
        with db.session_scope() as session:
            creator = ModelJobGroupCreator(session, '12', data)
            group = ModelJobGroup(name='group', uuid='uuid', status=GroupCreateStatus.PENDING)
            session.add(group)
            session.flush()
            flag, msg = creator.abort()
            self.assertTrue(flag)
            self.assertEqual(group.status, GroupCreateStatus.FAILED)


if __name__ == '__main__':
    unittest.main()

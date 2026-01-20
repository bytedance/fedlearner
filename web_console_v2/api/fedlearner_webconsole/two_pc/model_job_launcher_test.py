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
from google.protobuf.struct_pb2 import Value

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.initial_db import _insert_or_update_templates
from fedlearner_webconsole.algorithm.models import AlgorithmType, Algorithm
from fedlearner_webconsole.two_pc.model_job_launcher import ModelJobLauncher
from fedlearner_webconsole.workflow.models import WorkflowState
from fedlearner_webconsole.mmgr.models import ModelJob, ModelJobGroup, ModelJobType, ModelJobRole
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobState, DatasetJobKind, DatasetType, \
    DatasetJobStage
from fedlearner_webconsole.proto.two_pc_pb2 import CreateModelJobData, \
    TransactionData
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, JobDefinition
from fedlearner_webconsole.proto.common_pb2 import Variable


def _get_workflow_config():
    return WorkflowDefinition(job_definitions=[
        JobDefinition(name='train-job',
                      job_type=JobDefinition.JobType.NN_MODEL_TRANINING,
                      variables=[
                          Variable(name='mode', value='train'),
                          Variable(name='data_source',
                                   value='dataset-job-stage-uuid-psi-data-join-job',
                                   typed_value=Value(string_value='dataset-job-stage-uuid-psi-data-join-job')),
                          Variable(name='data_path', typed_value=Value(string_value='')),
                      ])
    ])


class ModelJobCreatorTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            _insert_or_update_templates(session)
            dataset_job = DatasetJob(id=1,
                                     name='datasetjob',
                                     uuid='dataset-job-uuid',
                                     state=DatasetJobState.SUCCEEDED,
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN)
            dataset = Dataset(id=2,
                              uuid='uuid',
                              name='datasetjob',
                              dataset_type=DatasetType.PSI,
                              path='/data/dataset/haha')
            dataset_job_stage = DatasetJobStage(id=1,
                                                name='data-join',
                                                uuid='dataset-job-stage-uuid',
                                                project_id=1,
                                                state=DatasetJobState.SUCCEEDED,
                                                dataset_job_id=1,
                                                data_batch_id=1)
            algorithm = Algorithm(id=2, name='algo')
            model_job_group = ModelJobGroup(name='group',
                                            uuid='uuid',
                                            project_id=1,
                                            algorithm_type=AlgorithmType.NN_VERTICAL,
                                            algorithm_id=2,
                                            role=ModelJobRole.PARTICIPANT,
                                            authorized=True,
                                            dataset_id=2,
                                            latest_version=2)
            model_job_group.set_config(_get_workflow_config())
            session.add_all([dataset_job, dataset_job_stage, dataset, model_job_group, algorithm])
            session.commit()

    def test_prepare(self):
        create_model_job_data = CreateModelJobData(model_job_name='model-job',
                                                   model_job_uuid='model-job-uuid',
                                                   group_uuid='uuid',
                                                   version=3)
        data = TransactionData(create_model_job_data=create_model_job_data)
        with db.session_scope() as session:
            # succeeded
            flag, _ = ModelJobLauncher(session, tid='12', data=data).prepare()
            self.assertTrue(flag)
        with db.session_scope() as session:
            # fail due to group is not authorized
            group: ModelJobGroup = session.query(ModelJobGroup).filter_by(uuid='uuid').first()
            group.authorized = False
            flag, msg = ModelJobLauncher(session, tid='12', data=data).prepare()
            self.assertFalse(flag)
            self.assertEqual(msg, 'model group uuid not authorized to coordinator')
        with db.session_scope() as session:
            # fail due to algorithm not found
            group: ModelJobGroup = session.query(ModelJobGroup).filter_by(uuid='uuid').first()
            group.algorithm_id = 3
            data = TransactionData(create_model_job_data=create_model_job_data)
            flag, msg = ModelJobLauncher(session, tid='12', data=data).prepare()
            self.assertFalse(flag)
            self.assertEqual(msg, 'the algorithm 3 of group group is not found')
        with db.session_scope() as session:
            # fail due to group is not configured
            group: ModelJobGroup = session.query(ModelJobGroup).filter_by(uuid='uuid').first()
            group.config = None
            flag, msg = ModelJobLauncher(session, tid='12', data=data).prepare()
            self.assertFalse(flag)
            self.assertEqual(msg, 'the config of model group group not found')
        with db.session_scope() as session:
            # fail due to group is not found
            data.create_model_job_data.group_uuid = '1'
            flag, msg = ModelJobLauncher(session, tid='12', data=data).prepare()
            self.assertFalse(flag)
            self.assertEqual(msg, 'model group not found by uuid 1')
            data.create_model_job_data.group_uuid = 'uuid'
            # fail due to version mismatch
            data.create_model_job_data.version = 2
            flag, msg = ModelJobLauncher(session, tid='12', data=data).prepare()
            self.assertFalse(flag)
            self.assertEqual(msg,
                             'the latest version of model group group is larger than or equal to the given version')

    def test_commit(self):
        create_model_job_data = CreateModelJobData(model_job_name='model-job',
                                                   model_job_uuid='model-job-uuid',
                                                   group_uuid='uuid',
                                                   version=2)
        data = TransactionData(create_model_job_data=create_model_job_data)
        with db.session_scope() as session:
            flag, msg = ModelJobLauncher(session, tid='12', data=data).commit()
            self.assertTrue(flag)
            session.commit()
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).filter_by(uuid='uuid').first()
            model_job: ModelJob = session.query(ModelJob).filter_by(name='model-job').first()
            self.assertEqual(model_job.group_id, group.id)
            self.assertTrue(model_job.project_id, group.project_id)
            self.assertTrue(model_job.algorithm_type, group.algorithm_type)
            self.assertTrue(model_job.model_job_type, ModelJobType.TRAINING)
            self.assertTrue(model_job.dataset_id, group.dataset_id)
            self.assertEqual(model_job.workflow.get_config(), group.get_config())
            self.assertEqual(model_job.workflow.state, WorkflowState.READY)
            self.assertTrue(model_job.version, 2)
            self.assertTrue(group.latest_version, 2)


if __name__ == '__main__':
    unittest.main()

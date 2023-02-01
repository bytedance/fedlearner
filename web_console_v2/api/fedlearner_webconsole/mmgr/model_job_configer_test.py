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
import tempfile
import unittest
from datetime import datetime
from envs import Envs
from unittest.mock import patch
from google.protobuf.struct_pb2 import Value

from testing.common import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.initial_db import _insert_or_update_templates
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.mmgr.models import Model, ModelJobType
from fedlearner_webconsole.mmgr.model_job_configer import ModelJobConfiger, get_sys_template_id, set_load_model_name
from fedlearner_webconsole.algorithm.models import Algorithm, AlgorithmProject, AlgorithmType
from fedlearner_webconsole.algorithm.utils import algorithm_cache_path
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobState, DatasetJobKind, DatasetType, \
    DatasetJobStage, DataBatch
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from fedlearner_webconsole.workflow_template.utils import make_variable
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobConfig
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, JobDefinition
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmParameter, AlgorithmVariable
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.utils.proto import to_dict, remove_secrets


def _get_config() -> WorkflowDefinition:
    return WorkflowDefinition(job_definitions=[
        JobDefinition(variables=[
            Variable(name='data_source'),
            Variable(name='data_path'),
            Variable(name='file_wildcard'),
        ])
    ])


def _set_config(config: WorkflowDefinition, name: str, value: str):
    for var in config.job_definitions[0].variables:
        if var.name == name:
            var.value = value
            var.typed_value.MergeFrom(Value(string_value=value))
            var.value_type = Variable.ValueType.STRING


class UtilsTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            _insert_or_update_templates(session)
            session.commit()

    def test_get_template(self):
        with db.session_scope() as session:
            template_id = get_sys_template_id(session,
                                              AlgorithmType.TREE_VERTICAL,
                                              model_job_type=ModelJobType.TRAINING)
            self.assertEqual(session.query(WorkflowTemplate).get(template_id).name, 'sys-preset-tree-model')
            template_id = get_sys_template_id(session, AlgorithmType.NN_VERTICAL, model_job_type=ModelJobType.TRAINING)
            self.assertEqual(session.query(WorkflowTemplate).get(template_id).name, 'sys-preset-nn-model')
            template_id = get_sys_template_id(session,
                                              AlgorithmType.NN_HORIZONTAL,
                                              model_job_type=ModelJobType.TRAINING)
            self.assertEqual(session.query(WorkflowTemplate).get(template_id).name, 'sys-preset-nn-horizontal-model')
            template_id = get_sys_template_id(session,
                                              AlgorithmType.NN_HORIZONTAL,
                                              model_job_type=ModelJobType.EVALUATION)
            self.assertEqual(
                session.query(WorkflowTemplate).get(template_id).name, 'sys-preset-nn-horizontal-eval-model')

    def test_set_load_model_name(self):
        config = ModelJobConfig(algorithm_uuid='uuid', variables=[Variable(name='load_model_name')])
        set_load_model_name(config, 'test-model')
        expected_config = ModelJobConfig(algorithm_uuid='uuid',
                                         variables=[
                                             Variable(name='load_model_name',
                                                      value='test-model',
                                                      typed_value=Value(string_value='test-model'),
                                                      value_type=Variable.ValueType.STRING)
                                         ])
        self.assertEqual(config, expected_config)
        config = ModelJobConfig(algorithm_uuid='uuid', variables=[Variable(name='test')])
        set_load_model_name(config, 'test-model')
        expected_config = ModelJobConfig(algorithm_uuid='uuid', variables=[Variable(name='test')])
        self.assertEqual(config, expected_config)


class ModelJobConfigerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        project = Project(id=1, name='project')
        participant = Participant(id=1, name='part', domain_name='test')
        project.participants = [participant]
        dataset_job = DatasetJob(id=1,
                                 name='data-join',
                                 uuid='dataset-job-uuid',
                                 project_id=1,
                                 state=DatasetJobState.SUCCEEDED,
                                 kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                 input_dataset_id=1,
                                 output_dataset_id=2,
                                 workflow_id=1)
        dataset_job_stage = DatasetJobStage(id=1,
                                            name='data-join',
                                            uuid='dataset-job-stage-uuid',
                                            project_id=1,
                                            state=DatasetJobState.SUCCEEDED,
                                            dataset_job_id=1,
                                            data_batch_id=1)
        workflow = Workflow(id=1, uuid='workflow-uuid', name='workflow')
        dataset = Dataset(id=2, uuid='uuid', name='datasetjob', dataset_type=DatasetType.PSI, path='/data/dataset/haha')
        data_batch = DataBatch(id=1,
                               name='20221213',
                               dataset_id=1,
                               path='/data/dataset/haha/batch/20221213',
                               event_time=datetime(2022, 12, 13, 16, 37, 37))
        algorithm_project = AlgorithmProject(id=1,
                                             name='algo-project',
                                             uuid='uuid',
                                             type=AlgorithmType.NN_VERTICAL,
                                             path='/data/algorithm_project/uuid')
        algorithm = Algorithm(id=1,
                              name='algo',
                              uuid='uuid',
                              type=AlgorithmType.NN_VERTICAL,
                              path='/data/algorithm/uuid',
                              algorithm_project_id=1)
        parameter = AlgorithmParameter()
        parameter.variables.extend([AlgorithmVariable(name='EMBED_SIZE', value='128')])
        algorithm.set_parameter(parameter=parameter)
        job = Job(id=1,
                  name='uuid-train-job',
                  workflow_id=1,
                  project_id=1,
                  job_type=JobType.NN_MODEL_TRANINING,
                  state=JobState.COMPLETED)
        model = Model(id=2, name='model', job_id=1)
        with db.session_scope() as session:
            _insert_or_update_templates(session)
            session.add_all([
                project, participant, dataset_job, dataset_job_stage, dataset, algorithm, algorithm_project, model, job,
                workflow, data_batch
            ])
            session.commit()

    def test_get_config(self):
        with db.session_scope() as session:
            parameter = AlgorithmParameter(variables=[AlgorithmVariable(name='EMBED_SIZE', value='256')])
            model_job_config = ModelJobConfig(
                algorithm_uuid='uuid',
                algorithm_parameter=parameter,
                variables=[Variable(name='sparse_estimator', typed_value=Value(string_value='true'))])
            configer = ModelJobConfiger(session, ModelJobType.TRAINING, AlgorithmType.NN_VERTICAL, 1)
            config = configer.get_config(dataset_id=2, model_id=2, model_job_config=model_job_config)
            self.assertEqual(config.job_definitions[0].job_type, JobDefinition.JobType.NN_MODEL_TRANINING)
            self.assertEqual(len(config.job_definitions), 1)
            var_dict = {var.name: var for var in config.job_definitions[0].variables}
            self.assertEqual(var_dict['load_model_name'].typed_value, Value(string_value='uuid-train-job'))
            self.assertEqual(var_dict['data_source'].typed_value,
                             Value(string_value='dataset-job-stage-uuid-psi-data-join-job'))
            self.assertEqual(var_dict['mode'].typed_value, Value(string_value='train'))
            self.assertEqual(var_dict['sparse_estimator'].typed_value, Value(string_value='true'))
            self.assertEqual(
                to_dict(var_dict['algorithm'].typed_value), {
                    'algorithmId': 1.0,
                    'algorithmUuid': 'uuid',
                    'algorithmProjectUuid': 'uuid',
                    'config': [{
                        'comment': '',
                        'display_name': '',
                        'name': 'EMBED_SIZE',
                        'required': False,
                        'value': '256',
                        'value_type': 'STRING'
                    }],
                    'participantId': 0.0,
                    'path': '/data/algorithm/uuid',
                    'algorithmProjectId': 1.0
                })
            self.assertEqual(json.loads(var_dict['algorithm'].widget_schema), {
                'component': 'AlgorithmSelect',
                'required': True,
                'tag': 'OPERATING_PARAM'
            })

    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.get_algorithm_files')
    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.get_algorithm')
    def test_get_config_when_algorithm_from_participant(self, mock_get_algorithm, mock_get_algorithm_files):
        with db.session_scope() as session:
            algo = session.query(Algorithm).get(1).to_proto()
            algo.uuid = 'uuid-from-participant'
            mock_get_algorithm.return_value = remove_secrets(algo)
            parameter = AlgorithmParameter(variables=[AlgorithmVariable(name='EMBED_SIZE', value='256')])
            model_job_config = ModelJobConfig(
                algorithm_uuid='uuid-from-participant',
                algorithm_parameter=parameter,
                variables=[Variable(name='sparse_estimator', typed_value=Value(string_value='true'))])
            configer = ModelJobConfiger(session, ModelJobType.TRAINING, AlgorithmType.NN_VERTICAL, 1)
            with tempfile.TemporaryDirectory() as temp_dir:
                Envs.STORAGE_ROOT = temp_dir
                config = configer.get_config(dataset_id=2, model_id=2, model_job_config=model_job_config)
            var_dict = {var.name: var for var in config.job_definitions[0].variables}
            self.assertEqual(
                to_dict(var_dict['algorithm'].typed_value), {
                    'algorithmId': 0,
                    'algorithmUuid': 'uuid-from-participant',
                    'algorithmProjectUuid': 'uuid',
                    'config': [{
                        'comment': '',
                        'display_name': '',
                        'name': 'EMBED_SIZE',
                        'required': False,
                        'value': '256',
                        'value_type': 'STRING'
                    }],
                    'participantId': 1.0,
                    'path': algorithm_cache_path(Envs.STORAGE_ROOT, 'uuid-from-participant'),
                    'algorithmProjectId': 0
                })

    def test_get_dataset_variables(self):
        with db.session_scope() as session:
            # test for config RSA dataset for tree
            configer = ModelJobConfiger(session=session,
                                        model_job_type=ModelJobType.TRAINING,
                                        algorithm_type=AlgorithmType.TREE_VERTICAL,
                                        project_id=1)
            variables = configer.get_dataset_variables(dataset_id=2)
            expected_variables = [
                make_variable(name='data_source', typed_value='dataset-job-stage-uuid-psi-data-join-job'),
                make_variable(name='data_path', typed_value=''),
                make_variable(name='file_wildcard', typed_value='*.data'),
            ]
            self.assertEqual(variables, expected_variables)
            # test for config RSA dataset for NN
            config = _get_config()
            configer = ModelJobConfiger(session=session,
                                        model_job_type=ModelJobType.TRAINING,
                                        algorithm_type=AlgorithmType.NN_VERTICAL,
                                        project_id=1)
            variables = configer.get_dataset_variables(dataset_id=2)
            expected_variables = [
                make_variable(name='data_source', typed_value='dataset-job-stage-uuid-psi-data-join-job'),
                make_variable(name='data_path', typed_value='')
            ]
            self.assertEqual(variables, expected_variables)
            # test for config RSA dataset when datset_job_stage is None
            dataset_job_stage = session.query(DatasetJobStage).get(1)
            dataset_job_stage.dataset_job_id = 2
            session.flush()
            configer = ModelJobConfiger(session=session,
                                        model_job_type=ModelJobType.TRAINING,
                                        algorithm_type=AlgorithmType.NN_VERTICAL,
                                        project_id=1)
            variables = configer.get_dataset_variables(dataset_id=2)
            expected_variables = [
                make_variable(name='data_source', typed_value='workflow-uuid-psi-data-join-job'),
                make_variable(name='data_path', typed_value='')
            ]
            self.assertEqual(variables, expected_variables)

        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            dataset_job.kind = DatasetJobKind.OT_PSI_DATA_JOIN
            session.commit()
        with db.session_scope() as session:
            # test for config OT dataset for tree
            configer = ModelJobConfiger(session=session,
                                        model_job_type=ModelJobType.TRAINING,
                                        algorithm_type=AlgorithmType.TREE_VERTICAL,
                                        project_id=1)
            variables = configer.get_dataset_variables(dataset_id=2)
            expected_variables = [
                make_variable(name='data_source', typed_value=''),
                make_variable(name='data_path', typed_value='/data/dataset/haha/batch'),
                make_variable(name='file_wildcard', typed_value='**/part*'),
            ]
            self.assertEqual(variables, expected_variables)
            # test for config OT dataset for nn
            configer = ModelJobConfiger(session=session,
                                        model_job_type=ModelJobType.TRAINING,
                                        algorithm_type=AlgorithmType.NN_VERTICAL,
                                        project_id=1)
            variables = configer.get_dataset_variables(dataset_id=2)
            expected_variables = [
                make_variable(name='data_source', typed_value=''),
                make_variable(name='data_path', typed_value='/data/dataset/haha/batch'),
            ]
            self.assertEqual(variables, expected_variables)
            # test when data_batch_id is set
            configer = ModelJobConfiger(session=session,
                                        model_job_type=ModelJobType.TRAINING,
                                        algorithm_type=AlgorithmType.NN_VERTICAL,
                                        project_id=1)
            variables = configer.get_dataset_variables(dataset_id=2, data_batch_id=1)
            expected_variables = [
                make_variable(name='data_source', typed_value=''),
                make_variable(name='data_path', typed_value='/data/dataset/haha/batch/20221213')
            ]
            self.assertEqual(variables, expected_variables)


if __name__ == '__main__':
    unittest.main()

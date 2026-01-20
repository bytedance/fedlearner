# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import base64
import tarfile
import unittest
from unittest.mock import patch
from envs import Envs
from io import BytesIO
from google.protobuf.json_format import ParseDict

from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.yaml_formatter import code_dict_encode, YamlFormatterService
from fedlearner_webconsole.job.models import Job, JobState, JobType
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.setting_pb2 import SystemVariables
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition
from fedlearner_webconsole.utils.pp_yaml import _format_yaml, GenerateDictService
from fedlearner_webconsole.workflow.models import Workflow  # pylint: disable=unused-import
from testing.no_web_server_test_case import NoWebServerTestCase

BASE_DIR = Envs.BASE_DIR


class YamlFormatterTest(NoWebServerTestCase):

    def test_format_with_phs(self):
        project = {'variables[0]': {'storage_root_dir': 'root_dir'}}
        workflow = {'jobs': {'raw_data_job': {'name': 'raw_data123'}}}
        yaml = _format_yaml("""
          {
            "name": "OUTPUT_BASE_DIR",
            "value": "${project.variables[0].storage_root_dir}/raw_data/${workflow.jobs.raw_data_job.name}"
          }
        """,
                            project=project,
                            workflow=workflow)
        self.assertEqual(
            yaml, """
          {
            "name": "OUTPUT_BASE_DIR",
            "value": "root_dir/raw_data/raw_data123"
          }
        """)

        self.assertEqual(_format_yaml('$project.variables[0].storage_root_dir', project=project),
                         project['variables[0]']['storage_root_dir'])

    def test_format_with_no_ph(self):
        self.assertEqual(_format_yaml('{a: 123, b: 234}'), '{a: 123, b: 234}')

    def test_format_yaml_unknown_ph(self):
        x = {'y': 123}
        with self.assertRaises(RuntimeError) as cm:
            _format_yaml('$x.y is $i.j.k', x=x)
        self.assertEqual(str(cm.exception), 'Unknown placeholder: i.j.k')
        with self.assertRaises(RuntimeError) as cm:
            _format_yaml('$x.y is ${i.j}', x=x)
        self.assertEqual(str(cm.exception), 'Unknown placeholder: i.j')

    def test_encode_code(self):
        test_data = {'test/a.py': 'awefawefawefawefwaef', 'test1/b.py': 'asdfasd', 'c.py': '', 'test/d.py': 'asdf'}
        code_base64 = code_dict_encode(test_data)
        code_dict = {}
        if code_base64.startswith('base64://'):
            tar_binary = BytesIO(base64.b64decode(code_base64[9:]))
            with tarfile.open(fileobj=tar_binary) as tar:
                for file in tar.getmembers():
                    code_dict[file.name] = str(tar.extractfile(file).read(), encoding='utf-8')
        self.assertEqual(code_dict, test_data)

    def test_generate_self_dict(self):
        config = {
            'variables': [{
                'name': 'namespace',
                'value': 'leader'
            }, {
                'name': 'basic_envs',
                'value': '{}'
            }, {
                'name': 'storage_root_dir',
                'value': '/'
            }]
        }
        job = Job(name='aa', project_id=1, workflow_id=1, state=JobState.NEW)
        job.set_config(ParseDict(config, JobDefinition()))
        self.assertEqual(
            YamlFormatterService.generate_self_dict(job), {
                'id': None,
                'crd_kind': None,
                'crd_meta': None,
                'name': 'aa',
                'job_type': None,
                'state': 'NEW',
                'is_disabled': None,
                'workflow_id': 1,
                'project_id': 1,
                'flapp_snapshot': None,
                'sparkapp_snapshot': None,
                'error_message': None,
                'created_at': None,
                'updated_at': None,
                'deleted_at': None,
                'complete_at': 0,
                'snapshot': None,
                'variables': {
                    'namespace': 'leader',
                    'basic_envs': '{}',
                    'storage_root_dir': '/',
                }
            })

    @patch('fedlearner_webconsole.setting.service.SettingService.get_application_version')
    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_variables')
    def test_generate_system_dict(self, mock_system_variables, mock_app_version):
        data = ParseDict({'variables': [{'name': 'a', 'value': 'b'}]}, SystemVariables())
        mock_system_variables.return_value = data
        mock_app_version.return_value.version.version = '2.2.2.2'
        with db.session_scope() as session:
            system_dict = GenerateDictService(session).generate_system_dict()
        self.assertTrue(isinstance(system_dict['basic_envs'], str))
        self.assertTrue(system_dict['version'], '2.2.2.2')
        self.assertEqual({'a': 'b'}, system_dict['variables'])
        self.assertEqual({'a': 'b'}, system_dict['variables'])

    def test_generate_project_dict(self):
        project = Project(name='project', comment='comment')
        participant = Participant(name='test-participant', domain_name='fl-test.com', host='127.0.0.1', port=32443)
        relationship = ProjectParticipant(project_id=1, participant_id=1)
        with db.session_scope() as session:
            session.add(project)
            session.add(participant)
            session.add(relationship)
            session.commit()
            project_dict = YamlFormatterService.generate_project_dict(project)
        result_dict = {'egress_domain': 'fl-test.com', 'egress_host': 'fl-test-client-auth.com'}
        self.assertEqual(project_dict['participants[0]'], result_dict)
        self.assertEqual(project_dict['participants'][0], result_dict)

    def test_generate_job_run_yaml(self):
        with db.session_scope() as session:
            project = Project(id=1, name='project 1')
            session.add(project)
            session.flush()
            job_def = JobDefinition(name='lonely_job', job_type=JobDefinition.ANALYZER)
            job_def.yaml_template = """
                   {
                       "apiVersion": "sparkoperator.k8s.io/v1beta2",
                       "kind": "SparkApplication",
                       "metadata": {
                           "name": self.name,
                       },

                   }
                   """
            job = Job(name='test', project_id=1, job_type=JobType(job_def.job_type), workflow_id=0)
            job.set_config(job_def)
            session.add(job)
            session.commit()
            result = YamlFormatterService(session).generate_job_run_yaml(job)
            self.assertEqual(
                result, {
                    'apiVersion': 'sparkoperator.k8s.io/v1beta2',
                    'kind': 'SparkApplication',
                    'metadata': {
                        'name': 'test',
                        'labels': {
                            'owner': 'no___workflow'
                        }
                    }
                })


if __name__ == '__main__':
    unittest.main()

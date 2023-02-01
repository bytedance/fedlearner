# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

from fedlearner_webconsole.job.yaml_formatter import\
    make_variables_dict
from fedlearner_webconsole.utils.pp_yaml import compile_yaml_template, GenerateDictService


def check_workflow_definition(workflow_definition, session):
    workflow = {
        'variables': make_variables_dict(workflow_definition.variables),
        'jobs': {},
        'uuid': 'test',
        'name': 'test',
        'id': 1,
        'creator': 'test'
    }
    project_stub = {
        'variables': {
            'storage_root_path': '/data'
        },
        'participants': [{
            'egress_domain': 'domain_name',
            'egress_host': 'client_auth'
        }],
        'id': 1,
        'name': 'test'
    }
    for job_def in workflow_definition.job_definitions:
        j_dic = {'variables': make_variables_dict(job_def.variables), 'name': 'other_job_name_stub'}
        workflow['jobs'][job_def.name] = j_dic
    for job_def in workflow_definition.job_definitions:
        # fake job name to pass the compiler_yaml_template
        self_dict = {'name': ' job_name_stub', 'variables': make_variables_dict(job_def.variables)}
        try:
            # check the result format
            compile_yaml_template(job_def.yaml_template, [],
                                  workflow=workflow,
                                  self=self_dict,
                                  system=GenerateDictService(session).generate_system_dict(),
                                  project=project_stub)
        except Exception as e:  # pylint: disable=broad-except
            raise ValueError(f'job_name: {job_def.name} Invalid python {str(e)}') from e

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
import base64
import json
import tarfile
from io import BytesIO

from fedlearner_webconsole.k8s.models import CrdKind
from fedlearner_webconsole.rpc.client import gen_egress_authority
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.utils.const import DEFAULT_OWNER_FOR_JOB_WITHOUT_WORKFLOW
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.utils.pp_yaml import compile_yaml_template, \
    add_username_in_label, GenerateDictService

CODE_TAR_FOLDER = 'code_tar'
CODE_TAR_FILE_NAME = 'code_tar.tar.gz'


def make_variables_dict(variables):
    var_dict = {}
    for var in variables:
        typed_value = to_dict(var.typed_value)
        if var.value_type == common_pb2.Variable.CODE:
            # if use or, then {} will be ignored.
            var_dict[var.name] = code_dict_encode(typed_value if typed_value is not None else json.loads(var.value))
        else:
            var_dict[var.name] = typed_value if typed_value is not None else var.value

    return var_dict


class YamlFormatterService:

    def __init__(self, session):
        self._session = session

    @staticmethod
    def generate_project_dict(proj):
        project = to_dict(proj.to_proto())
        variables = proj.get_variables()
        project['variables'] = make_variables_dict(variables)
        project['participants'] = []
        for index, participant in enumerate(proj.participants):
            # TODO(xiangyuxuan.prs): remove keys such as participants[0] in future.
            project[f'participants[{index}]'] = {}
            project[f'participants[{index}]']['egress_domain'] = \
                participant.domain_name
            project[f'participants[{index}]']['egress_host'] = gen_egress_authority(participant.domain_name)
            project['participants'].append(project[f'participants[{index}]'])
        return project

    def generate_workflow_dict(self, wf: 'Workflow'):
        workflow = wf.to_dict()
        workflow['variables'] = make_variables_dict(wf.get_config().variables)
        workflow['jobs'] = {}
        jobs = wf.get_jobs(self._session)
        for j in jobs:
            variables = make_variables_dict(j.get_config().variables)
            j_dic = j.to_dict()
            j_dic['variables'] = variables
            workflow['jobs'][j.get_config().name] = j_dic
        return workflow

    @staticmethod
    def generate_self_dict(j: 'Job'):
        job = j.to_dict()
        job['variables'] = make_variables_dict(j.get_config().variables)
        return job

    def generate_job_run_yaml(self, job: 'Job') -> dict:
        result_dict = compile_yaml_template(job.get_config().yaml_template,
                                            use_old_formater=job.crd_kind is None or
                                            job.crd_kind == CrdKind.FLAPP.value,
                                            post_processors=[
                                                lambda loaded_json: add_username_in_label(
                                                    loaded_json, job.workflow.creator
                                                    if job.workflow else DEFAULT_OWNER_FOR_JOB_WITHOUT_WORKFLOW)
                                            ],
                                            workflow=job.workflow and self.generate_workflow_dict(job.workflow),
                                            project=self.generate_project_dict(job.project),
                                            system=GenerateDictService(self._session).generate_system_dict(),
                                            self=self.generate_self_dict(job))
        return result_dict


def code_dict_encode(data_dict):
    # if data_dict is a dict ,
    # parse it to a tar file represented as base64 string
    assert isinstance(data_dict, dict)
    out = BytesIO()
    with tarfile.open(fileobj=out, mode='w:gz') as tar:
        for path in data_dict:
            data = data_dict[path].encode('utf-8')
            tarinfo = tarfile.TarInfo(path)
            tarinfo.size = len(data)
            tar.addfile(tarinfo, BytesIO(data))
    result = str(base64.b64encode(out.getvalue()), encoding='utf-8')
    return f'base64://{result}'

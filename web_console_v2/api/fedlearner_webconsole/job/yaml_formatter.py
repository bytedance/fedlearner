# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
import json
import tarfile
from io import BytesIO
import base64
from string import Template
from flatten_dict import flatten
from fedlearner_webconsole.utils.system_envs import get_system_envs
from fedlearner_webconsole.proto import common_pb2

class _YamlTemplate(Template):
    delimiter = '$'
    # Which placeholders in the template should be interpreted
    idpattern = r'[a-zA-Z_\-\[0-9\]]+(\.[a-zA-Z_\-\[0-9\]]+)*'


def format_yaml(yaml, **kwargs):
    """Formats a yaml template.

    Example usage:
        format_yaml('{"abc": ${x.y}}', x={'y': 123})
    output should be  '{"abc": 123}'
    """
    template = _YamlTemplate(yaml)
    try:
        return template.substitute(flatten(kwargs or {},
                                           reducer='dot'))
    except KeyError as e:
        raise RuntimeError(
            'Unknown placeholder: {}'.format(e.args[0])) from e


def make_variables_dict(variables):
    var_dict = {
        var.name: (
            code_dict_encode(json.loads(var.value))
                if var.value_type == common_pb2.Variable.ValueType.CODE \
                    else var.value)
        for var in variables
    }
    return var_dict


def generate_system_dict():
    return {'basic_envs': get_system_envs()}


def generate_project_dict(proj):
    project = proj.to_dict()
    project['variables'] = make_variables_dict(
        proj.get_config().variables)
    participants = project['config']['participants']
    for index, participant in enumerate(participants):
        project[f'participants[{index}]'] = {}
        project[f'participants[{index}]']['egress_domain'] =\
            participant['domain_name']
        project[f'participants[{index}]']['egress_host'] = \
            participant['grpc_spec']['authority']
    return project


def generate_workflow_dict(wf):
    workflow = wf.to_dict()
    workflow['variables'] = make_variables_dict(
        wf.get_config().variables)
    workflow['jobs'] = {}
    for j in wf.get_jobs():
        variables = make_variables_dict(j.get_config().variables)
        j_dic = j.to_dict()
        j_dic['variables'] = variables
        workflow['jobs'][j.get_config().name] = j_dic
    return workflow


def generate_job_run_yaml(job):
    yaml = format_yaml(job.get_config().yaml_template,
                       workflow=generate_workflow_dict(job.workflow),
                       project=generate_project_dict(job.project),
                       system=generate_system_dict())

    try:
        loaded = json.loads(yaml)
    except Exception as e:  # pylint: disable=broad-except
        raise ValueError(f'Invalid json {repr(e)}: {yaml}')
    return loaded


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

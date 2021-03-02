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
import os
from string import Template
from flatten_dict import flatten
from fedlearner_webconsole.utils.system_envs import get_system_envs

class _YamlTemplate(Template):
    delimiter = '$'
    # Which placeholders in the template should be interpreted
    idpattern = r'[a-zA-Z_-]+(\.[a-zA-Z_-]+)*'


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
        var.name: var.value
        for var in variables
    }
    return var_dict


def job_run_yaml(job):
    system_dict = {'basic_envs': get_system_envs()}
    workflow = job.workflow.to_dict()
    workflow['variables'] = make_variables_dict(
        job.workflow.get_config().variables)

    workflow['jobs'] = {}
    for j in job.workflow.get_jobs():
        variables = make_variables_dict(j.get_config().variables)
        j_dic = j.to_dict()
        j_dic['variables'] = variables
        workflow['jobs'][j.get_config().name] = j_dic
    project = job.project.to_dict()
    project['variables'] = make_variables_dict(
        job.project.get_config().variables)
    # set default values in project.variables
    if 'basic_envs' not in project['variables']:
        project['variables']['basic_envs'] = \
            '{"name":"DEFAULT_BASIC_ENVS", "value":""}'
    if 'storage_root_dir' not in project['variables']:
        project['variables']['storage_root_dir'] = os.environ.get(
            'STORAGE_ROOT', '/data')
    if 'egress_domain' not in project['variables']:
        # TODO: should adapt to multi_participants
        project['variables']['egress_domain'] = project[
            'config']['participants'][0]['domain_name']
    if 'egress_host' not in project['variables']:
        string_list = project['variables']['egress_domain'].split('.')
        # Splicing rule may be changed
        project['variables']['egress_host'] = '{}-client-auth{}'. \
            format(string_list[0], string_list[1])
    yaml = format_yaml(job.yaml_template,
                       workflow=workflow,
                       project=project,
                       system=system_dict)
    yaml = json.loads(yaml)
    return yaml

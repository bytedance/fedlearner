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
    # TODO: should adapt to multi_participants
    project['participants']['egress_domain'] = project[
            'config']['participants'][0]['domain_name']
    project['participants']['egress_host'] = project[
            'config']['participants'][0]['grpc_spec']['authority']
    yaml = format_yaml(job.yaml_template,
                       workflow=workflow,
                       project=project,
                       system=system_dict)
    yaml = json.loads(yaml)
    return yaml

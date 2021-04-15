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
from string import Template
from flatten_dict import flatten
from fedlearner_webconsole.job.yaml_formatter import make_variables_dict


class YamlTemplate(Template):
    """This formatter is used to format placeholders
    only can be observed in workflow_template module.
    """
    delimiter = '$'

    # overwrite this func to escape the invalid placeholder such as
    def _substitute(self, mapping, fixed_placeholder=None,
                    ignore_invalid=False):
        # Helper function for .sub()
        def convert(mo):
            # Check the most common path first.
            named = mo.group('named') or mo.group('braced')
            if named is not None:
                if fixed_placeholder is not None:
                    return fixed_placeholder
                return str(mapping[named])
            if mo.group('escaped') is not None:
                return self.delimiter
            if mo.group('invalid') is not None:
                # overwrite to escape invalid placeholder
                if ignore_invalid:
                    return mo.group()
                self._invalid(mo)
            raise ValueError('Unrecognized named group in pattern',
                             self.pattern)

        return self.pattern.sub(convert, self.template)


class _YamlTemplateOnlyFillWorkflow(YamlTemplate):
    """This formatter is used to format placeholders
    only can be observed in workflow_template module.
    """
    # Which placeholders in the template should be interpreted
    idpattern = r'(?:workflow\.jobs\.[a-zA-Z_\-0-9\[\]]+|workflow|self)' \
                r'\.variables\.[a-zA-Z_\-0-9\[\]]+'

    def substitute(self, mapping):
        return super()._substitute(mapping,
                                   fixed_placeholder=None,
                                   ignore_invalid=True)


class _YamlTemplateFillAll(YamlTemplate):
    """
    This formatter is used to format all valid placeholders with {}
    """
    # Which placeholders in the template should be interpreted
    idpattern = r'[a-zA-Z_\-\[0-9\]]+(\.[a-zA-Z_\-\[0-9\]]+)*'
    def substitute(self, mapping):
        return super()._substitute(mapping,
                                   fixed_placeholder='{}',
                                   ignore_invalid=False)


def format_yaml(yaml, **kwargs):
    """Formats a yaml template.

    Example usage:
        format_yaml('{"abc": ${x.y}}', x={'y': 123})
    output should be  '{"abc": 123}'
    """
    template = _YamlTemplateOnlyFillWorkflow(yaml)
    try:
        # checkout whether variables which can be observed at workflow_template
        # module is consistent with placeholders in string
        format_workflow = template.substitute(flatten(kwargs or {},
                                           reducer='dot'))
    except KeyError as e:
        raise ValueError(
            f'Unknown placeholder: {e.args[0]}') from e
    template = _YamlTemplateFillAll(format_workflow)
    try:
        # checkout whether other placeholders are valid and
        # format them with {} in order to go ahead to next step,
        # json format check
        return template.substitute(flatten(kwargs or {},
                                               reducer='dot'))
    except ValueError as e:
        raise ValueError(f'Wrong placeholder: {str(e)} . '
                         f'Origin yaml: {format_workflow}')


def check_workflow_definition(workflow_definition):
    workflow = {'variables': make_variables_dict(workflow_definition.variables),
                'jobs': {}}
    for job_def in workflow_definition.job_definitions:
        j_dic = {'variables': make_variables_dict(job_def.variables)}
        workflow['jobs'][job_def.name] = j_dic

    for job_def in workflow_definition.job_definitions:
        self_dict = {'variables': make_variables_dict(job_def.variables)}
        try:
            # check placeholders
            yaml = format_yaml(job_def.yaml_template,
                               workflow=workflow,
                               self=self_dict)
        except ValueError as e:
            raise ValueError(f'job_name: {job_def.name} '
                             f'Invalid placeholder: {str(e)}')
        try:
            # check json format
            loaded = json.loads(yaml)
        except Exception as e:  # pylint: disable=broad-except
            raise ValueError(f'job_name: {job_def.name} Invalid '
                             f'json {repr(e)}: {yaml}')

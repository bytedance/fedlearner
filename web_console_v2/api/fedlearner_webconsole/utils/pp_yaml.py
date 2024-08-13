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
import logging
import json
from ast import Attribute, Name, Subscript, Add, Call
from string import Template
from typing import Callable, List, Optional
from simpleeval import EvalWithCompoundTypes
from fedlearner_webconsole.utils.pp_flatten_dict import flatten
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.utils.const import DEFAULT_OWNER
from fedlearner_webconsole.utils.system_envs import get_system_envs


class _YamlTemplate(Template):
    delimiter = '$'
    # Which placeholders in the template should be interpreted
    idpattern = r'[a-zA-Z_\-\[0-9\]]+(\.[a-zA-Z_\-\[0-9\]]+)*'


def _format_yaml(yaml, **kwargs):
    """Formats a yaml template.

    Example usage:
        format_yaml('{"abc": ${x.y}}', x={'y': 123})
    output should be  '{"abc": 123}'
    """
    template = _YamlTemplate(yaml)
    try:
        return template.substitute(flatten(kwargs or {}))
    except KeyError as e:
        raise RuntimeError(f'Unknown placeholder: {e.args[0]}') from e


def _to_str(x=None) -> str:
    if x is None:
        return ''
    if isinstance(x, dict):
        return json.dumps(x)
    return str(x)


def _to_int(x=None) -> Optional[int]:
    if x is None or x == '':
        return None
    try:
        return int(float(x))
    except Exception as e:
        raise ValueError(f'{str(e)}. The input is: {x}') from e


def _to_float(x=None) -> Optional[float]:
    if x is None or x == '':
        return None
    try:
        return float(x)
    except Exception as e:
        raise ValueError(f'{str(e)}. The input is: {x}') from e


def _to_bool(x=None) -> bool:
    if x is None or x == '':
        return False
    if isinstance(x, bool):
        return x
    if not isinstance(x, str):
        raise ValueError(f'{x} can not convert boolean')
    if x.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    if x.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    raise ValueError(f'{x} can not convert boolean')


def _to_dict(x) -> dict:
    if isinstance(x, dict):
        return x
    raise ValueError(f'{x} is not dict')


def _to_list(x) -> list:
    if isinstance(x, list):
        return x
    raise ValueError(f'{x} is not list')


def _eval_attribute(self, node):
    """
    Copy from simpleeval, and modified the last exception raising to has more information about the attribute.
    Before changed, the exception message would be "can't find 'c'", when can't find the attribute c in a.b.
     Such as eval('a.b.c', names:{'a':{'b': {'d':1}}}).
    After changed, the exception message will be "can't find 'a.b.c'".
    """
    max_depth = 10
    for prefix in ['_', 'func_']:
        if node.attr.startswith(prefix):
            raise ValueError('Sorry, access to __attributes '
                             ' or func_ attributes is not available. '
                             f'({node.attr})')
    if node.attr in ['format', 'format_map', 'mro']:
        raise ValueError(f'Sorry, this method is not available. ({node.attr})')
    # eval node
    node_evaluated = self._eval(node.value)  # pylint: disable=protected-access

    # Maybe the base object is an actual object, not just a dict
    try:
        return getattr(node_evaluated, node.attr)
    except (AttributeError, TypeError):
        pass

    if self.ATTR_INDEX_FALLBACK:
        try:
            return node_evaluated[node.attr]
        except (KeyError, TypeError):
            pass

    # If it is neither, raise an exception
    # Modified(xiangyuxuan.prs) from simpleeval to make the error message has more information.
    pre_node = node.value
    attr_chains = [node.attr]
    for i in range(max_depth):
        if not isinstance(pre_node, Attribute):
            break
        attr_chains.append(pre_node.attr)
        pre_node = pre_node.value
    if isinstance(pre_node, Name):
        attr_chains.append(pre_node.id)
    raise ValueError('.'.join(attr_chains[::-1]), self.expr)


def compile_yaml_template(yaml_template: str,
                          post_processors: List[Callable],
                          ignore_variables: bool = False,
                          use_old_formater: bool = False,
                          **kwargs) -> dict:
    """
    Args:
        yaml_template (str): The original string to format.
        post_processors (List): List of methods to process the dict which yaml_template generated.
        ignore_variables (bool): If True then Compile the yaml_template without any variables.
        All variables will be treated as None. Such as: "{var_a.attr_a: 1, 'b': 2}" -> {None:1, 'b':2}
        **kwargs: variables to format the yaml_template.
        use_old_formater (bool): If True then use old ${} placeholder formatter.
    Raises:
        ValueError: foramte failed
    Returns:
        a dict which can submit to k8s.
    """
    # TODO(xiangyuxuan.prs): this is old version formatter, should be deleted after no flapp in used
    if use_old_formater:
        yaml_template = _format_yaml(yaml_template, **kwargs)
    try:
        # names={'true': True, 'false': False, 'null': None} support json symbol in python
        eval_with_types = EvalWithCompoundTypes(names={'true': True, 'false': False, 'null': None, **kwargs})

        # replace the built-in functions in eval stage,
        # Ref: https://github.com/danthedeckie/simpleeval
        if ignore_variables:
            eval_with_types.nodes[Attribute] = lambda x: None
            eval_with_types.nodes[Name] = lambda x: None
            eval_with_types.nodes[Subscript] = lambda x: None
            eval_with_types.nodes[Call] = lambda x: None
            eval_with_types.operators[Add] = lambda x, y: None
            return eval_with_types.eval(yaml_template)
        eval_with_types.functions.update(str=_to_str, int=_to_int, bool=_to_bool, dict=_to_dict, list=_to_list)

        # Overwrite to let the exceptions message have more information.
        eval_with_types.nodes[Attribute] = lambda x: _eval_attribute(eval_with_types, x)
        loaded_json = eval_with_types.eval(yaml_template)
    except SyntaxError as e:
        raise ValueError(f'Invalid python dict syntax error msg: {e.args}') from e
    except Exception as e:  # pylint: disable=broad-except
        # use args[0] to simplify the error message
        raise ValueError(f'Invalid python dict placeholder error msg: {e.args[0]}') from e
    # post processor for flapp yaml
    for post_processor in post_processors:
        loaded_json = post_processor(loaded_json)
    return loaded_json


def add_username_in_label(loaded_json: dict, username: Optional[str] = None) -> dict:
    if 'labels' not in loaded_json['metadata']:
        loaded_json['metadata']['labels'] = {}
    loaded_json['metadata']['labels']['owner'] = username or DEFAULT_OWNER
    return loaded_json


class GenerateDictService:

    def __init__(self, session):
        self._session = session

    def generate_system_dict(self):
        sys_vars_dict = SettingService(self._session).get_system_variables_dict()
        # TODO(xiangyuxuan.prs): basic_envs is old method to inject the envs, delete in the future.
        basic_envs_list = get_system_envs()
        basic_envs = ','.join([json.dumps(env) for env in basic_envs_list])
        version = SettingService(self._session).get_application_version().version.version
        return {
            'basic_envs': basic_envs,
            'variables': sys_vars_dict,
            'basic_envs_list': basic_envs_list,
            'version': version
        }


def _envs_to_dict(flapp_envs: List[dict]) -> dict:
    return {env['name']: env['value'] for env in flapp_envs}


def extract_flapp_envs(flapp_json: dict) -> Optional[dict]:
    """Extract flapp envs

    Returns:
        dict of environment variables under different type of pods is returned, e.g.
        {'master': {'INPUT_BASE_DIR': '/data'}
        'worker': {'INPUT_DATA_FORMAT': 'TF_RECORD'}}
    """
    try:
        if flapp_json['kind'] != 'FLApp':
            return None
        flapp_specs = flapp_json['spec']['flReplicaSpecs']
        flapp_envs = {}
        for role in flapp_specs:
            assert len(flapp_specs[role]['template']['spec']['containers']) == 1
            flapp_envs[role] = _envs_to_dict(flapp_specs[role]['template']['spec']['containers'][0]['env'])
        return flapp_envs
    except Exception as e:  # pylint: disable=broad-except
        logging.error(f'extracting environment variables with error {str(e)}')
        return None

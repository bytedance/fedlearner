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

from pathlib import Path


def replace_ref_name(schema: dict, ref_name: str, message_name: str) -> dict:
    for k, v in schema.items():
        if isinstance(v, dict):
            schema[k] = replace_ref_name(v, ref_name, message_name)
    if '$ref' in schema and schema['$ref'] == f'#/definitions/{message_name}':
        schema['$ref'] = f'#/definitions/{ref_name}'
    return schema


def remove_title(schema: dict) -> dict:
    for k, v in schema.items():
        if isinstance(v, dict):
            schema[k] = remove_title(v)
    if 'title' in schema:
        del schema['title']
    return schema


def normalize_schema(definitions: dict, jsonschema_path: Path) -> dict:
    # "prefix_schema_files_with_package" option in Makefile will generate a directory with
    # the name of the corresponding package name, therefore the full name of a message is
    # {directory_name}.{message_name}
    package_name = jsonschema_path.parent.name
    message_name = jsonschema_path.stem
    ref_name = f'{package_name}.{message_name}'

    # Title gets generated in newer version of jsonschema plugin; just remove it manually
    definitions = remove_title(definitions)

    # The name of the first message defined in .proto file will be the used as the generated
    # json file's name, which does not have a package name. Therefore, we prepend the package
    # name for it
    definitions[ref_name] = replace_ref_name(definitions[message_name], ref_name, message_name)
    del definitions[message_name]
    return definitions

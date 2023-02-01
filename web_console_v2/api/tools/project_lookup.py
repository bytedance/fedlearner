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

import argparse
import logging
from typing import List

import sys
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.utils.hooks import pre_start_hook


def lookup(var_names: List[str]):
    """Finds all projects which contains the specified variables (any of them)."""
    with db.session_scope() as session:
        projects = session.query(Project).all()
        for project in projects:
            filtered_variables = [var for var in project.get_variables() if var.name in var_names]
            if filtered_variables:
                logging.info('============================')
                logging.info(f'Project ID: {project.id}')
                logging.info(f'Project name: {project.name}')
                for var in filtered_variables:
                    logging.info(f'Var name: {var.name}, Var value: {var.typed_value}')


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Project cleanup')
    parser.add_argument('--variables', nargs='+', type=str, required=True, help='Variables to lookup')
    args = parser.parse_args()

    pre_start_hook()
    lookup(args.variables)

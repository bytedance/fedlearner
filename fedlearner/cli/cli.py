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

import click
from fedlearner.cli.commands.list import list as cli_list
from fedlearner.cli.commands.scheduler import scheduler
from fedlearner.cli.commands.create import create


@click.group('fl-cli')
def cli_group():
    pass


cli_group.add_command(create)
cli_group.add_command(cli_list)
cli_group.add_command(scheduler)

if __name__ == '__main__':
    cli_group()

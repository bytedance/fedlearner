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

import click
import logging
from pp_lite.data_join.psi_rsa import psi_client as psi_rsa_client
from pp_lite.data_join.psi_rsa import psi_server as psi_rsa_server
from pp_lite.data_join.psi_ot import client as psi_ot_and_hash_client
from pp_lite.data_join.psi_ot import server as psi_ot_and_hash_server
from pp_lite.data_join.psi_ot import arguments as psi_ot_and_hash_arguments
from pp_lite.proto.common_pb2 import DataJoinType

from web_console_v2.inspection.error_code import AreaCode, JobException, write_termination_message


@click.group(name='pp_lite')
def pp_lite():
    pass


# TODO(zhou.yi): add psi rsa options
@pp_lite.command()
@click.argument('role', type=click.Choice(['client', 'server', 'light_client']))
def psi_rsa(role: str):
    try:
        if role in ['client', 'light_client']:
            psi_rsa_client.run(psi_rsa_client.get_arguments())
        else:
            psi_rsa_server.run(psi_rsa_server.get_arguments())
    except JobException as e:
        logging.exception(e.message)
        write_termination_message(AreaCode.PSI_RSA, e.error_type, e.message)
        raise JobException(AreaCode.PSI_RSA, e.error_type, e.message) from e


# TODO(zhou.yi): add psi ot options
@pp_lite.command()
@click.argument('role', type=click.Choice(['client', 'server', 'light_client']))
def psi_ot(role: str):
    try:
        args = psi_ot_and_hash_arguments.get_arguments()
        args.data_join_type = DataJoinType.OT_PSI
        if role == 'client':
            args.partitioned = True
            psi_ot_and_hash_client.run(args)
        elif role == 'light_client':
            args.partitioned = False
            psi_ot_and_hash_client.run(args)
        else:
            psi_ot_and_hash_server.run(args)
    except JobException as e:
        logging.exception(e.message)
        write_termination_message(AreaCode.PSI_OT, e.error_type, e.message)
        raise JobException(AreaCode.PSI_OT, e.error_type, e.message) from e


# TODO(zhou.yi): add psi hash options
@pp_lite.command()
@click.argument('role', type=click.Choice(['client', 'server', 'light_client']))
def psi_hash(role: str):
    try:
        args = psi_ot_and_hash_arguments.get_arguments()
        args.data_join_type = DataJoinType.HASHED_DATA_JOIN
        if role == 'client':
            args.partitioned = True
            psi_ot_and_hash_client.run(args)
        elif role == 'light_client':
            args.partitioned = False
            psi_ot_and_hash_client.run(args)
        else:
            psi_ot_and_hash_server.run(args)
    except JobException as e:
        logging.exception(e.message)
        write_termination_message(AreaCode.PSI_HASH, e.error_type, e.message)
        raise JobException(AreaCode.PSI_HASH, e.error_type, e.message) from e


if __name__ == '__main__':
    pp_lite()

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

import logging.config
from os import getenv

from pp_lite.data_join import envs

from pp_lite.rpc.server import RpcServer
from pp_lite.data_join.psi_rsa.server.data_join_servicer import DataJoinServiceServicer
from pp_lite.data_join.psi_rsa.server.utils import load_private_rsa_key
from pp_lite.utils.logging_config import logging_config, log_path
from pp_lite.utils.tools import print_named_dict


def get_arguments():
    arguments = {
        'rsa_private_key_path': getenv('PRIVATE_KEY_PATH'),
        'input_dir': getenv('INPUT_DIR'),
        'output_dir': getenv('OUTPUT_DIR'),
        'signed_column': getenv('SIGNED_COLUMN', 'signed'),
        'key_column': getenv('KEY_COLUMN', 'raw_id'),
        'server_port': int(getenv('SERVER_PORT', '50051')),
        'batch_size': int(getenv('BATCH_SIZE', '4096')),
        'num_sign_parallel': int(getenv('NUM_SIGN_PARALLEL', '30'))
    }
    return arguments


def run(args: dict):
    logging.config.dictConfig(logging_config(file_path=log_path(log_dir=envs.STORAGE_ROOT)))
    print_named_dict(name='Server Arguments', target_dict=args)
    private_key = load_private_rsa_key(args['rsa_private_key_path'])
    servicer = DataJoinServiceServicer(private_key=private_key,
                                       input_dir=args['input_dir'],
                                       output_dir=args['output_dir'],
                                       signed_column=args['signed_column'],
                                       key_column=args['key_column'],
                                       batch_size=args['batch_size'],
                                       num_sign_parallel=args['num_sign_parallel'])
    server = RpcServer(servicer=servicer, listen_port=args['server_port'])
    server.start()
    server.wait()

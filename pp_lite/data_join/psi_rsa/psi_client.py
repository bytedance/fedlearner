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
import json
import logging.config
import os
from os import getenv
from pp_lite.data_join.utils.example_id_reader import ExampleIdReader
from pp_lite.proto.common_pb2 import FileType

from pp_lite.rpc.client import DataJoinClient
from pp_lite.data_join.psi_rsa.client.task_producer import TaskProducer
from pp_lite.utils.logging_config import logging_config, log_path
from pp_lite.utils.metrics import get_audit_value, show_audit_info
from pp_lite.utils.tools import get_partition_ids, print_named_dict


def str_as_bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    if v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    raise argparse.ArgumentTypeError('Boolean value expected.')


# TODO(zhou.yi): change to CLI arguments
def get_arguments():
    arguments = {
        'input_dir': getenv('INPUT_DIR', '/app/workdir/input'),
        'output_dir': getenv('OUTPUT_DIR', '/app/workdir/output'),
        'key_column': getenv('KEY_COLUMN', 'raw_id'),
        'server_port': int(getenv('SERVER_PORT', '50051')),
        'batch_size': int(getenv('BATCH_SIZE', '4096')),
        'num_sign_parallel': int(getenv('NUM_SIGN_PARALLEL', '20')),
        'partitioned': str_as_bool(getenv('PARTITIONED', 'false')),
        'log_dir': getenv('LOG_DIR', '/app/workdir/log/'),
    }
    arguments['worker_rank'] = int(getenv('INDEX', '0'))
    if getenv('NUM_WORKERS'):
        arguments['num_workers'] = int(getenv('NUM_WORKERS'))
    role = getenv('ROLE', '')
    if getenv('CLUSTER_SPEC') and role != 'light_client':
        cluster_spec = json.loads(getenv('CLUSTER_SPEC'))

        # Only accept CLUSTER_SPEC in cluster environment,
        # so that CLUSTER_SPEC from .env in light client environment can be omitted.
        if 'clusterSpec' in cluster_spec:
            arguments['num_workers'] = len(cluster_spec['clusterSpec']['Worker'])
    return arguments


def _show_client_audit():
    show_audit_info()
    intersection_rate = format(get_audit_value('Joined data count') / get_audit_value('Input data count') * 100, '.2f')
    logging.info('====================Result====================')
    logging.info(f'Intersection rate {intersection_rate} %')
    logging.info('Running log locate at workdir/log')
    logging.info('Data join result locate at workdir/output/joined')
    logging.info('==============================================')


def run(args: dict):
    if args.get('log_dir') is not None:
        if not os.path.exists(args['log_dir']):
            os.makedirs(args['log_dir'], exist_ok=True)
        logging.config.dictConfig(logging_config(file_path=log_path(args['log_dir'])))
    print_named_dict(name='Client Arguments', target_dict=args)
    client = DataJoinClient(args['server_port'])
    client.check_server_ready(timeout_seconds=60)
    reader = ExampleIdReader(input_path=args['input_dir'], file_type=FileType.CSV, key_column=args['key_column'])
    partition_list = [-1]
    # If the client and the server use the same logic to partition, the partition can be intersected one by one.
    # Otherwise, all client data intersect with all server data.
    if args['partitioned']:
        num_partitions = reader.num_partitions
        partition_list = get_partition_ids(worker_rank=args['worker_rank'],
                                           num_workers=args['num_workers'],
                                           num_partitions=num_partitions)

    task_producer = TaskProducer(client=client,
                                 reader=reader,
                                 output_dir=args['output_dir'],
                                 key_column=args['key_column'],
                                 batch_size=args['batch_size'],
                                 num_sign_parallel=args['num_sign_parallel'])
    for partition_id in partition_list:
        task_producer.run(partition_id=partition_id)
    _show_client_audit()
    client.finish()

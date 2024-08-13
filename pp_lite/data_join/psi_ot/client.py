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

import grpc
import time
import logging
import logging.config
import tempfile
import copy
from concurrent.futures import FIRST_EXCEPTION, ProcessPoolExecutor, wait

from pp_lite.data_join import envs

from pp_lite.proto.arguments_pb2 import Arguments
from pp_lite.proto.common_pb2 import DataJoinType, FileType
from pp_lite.rpc.data_join_control_client import DataJoinControlClient
from pp_lite.data_join.psi_ot.data_join_manager import DataJoinManager
from pp_lite.data_join.psi_ot.joiner.ot_psi_joiner import OtPsiJoiner
from pp_lite.data_join.psi_ot.joiner.hashed_data_joiner import HashedDataJoiner
from pp_lite.data_join.utils.example_id_writer import ExampleIdWriter
from pp_lite.data_join.utils.example_id_reader import ExampleIdReader, PartitionInfo
from pp_lite.data_join.utils.partitioner import Partitioner
from pp_lite.utils.logging_config import logging_config, log_path
from pp_lite.utils.tools import get_partition_ids


def wait_for_ready(client: DataJoinControlClient):
    while True:
        try:
            client.health_check()
            break
        except grpc.RpcError:
            logging.info('server is not ready')
        time.sleep(10)


def wait_for_ready_and_verify(client: DataJoinControlClient, num_partitions: int, num_workers: int):
    wait_for_ready(client=client)
    logging.info('[DataJoinControlClient] start verify parameter')
    resp = client.verify_parameter(num_partitions=num_partitions, num_workers=num_workers)
    logging.info(
        f'[DataJoinControlClient] Server num_partitions: {resp.num_partitions}, num_workers: {resp.num_workers}')
    # assert resp.succeeded, 'joiner must have the same parameters'
    if not resp.succeeded:
        if resp.num_partitions == 0:
            logging.info(f'[DataJoinControlClient] Server num_partitions: {resp.num_partitions}, sever quit.')
        logging.info('[DataJoinControlClient]joiner must have the same parameters')
        return False
    return True


def run_joiner(args: Arguments):
    logging.config.dictConfig(logging_config(file_path=log_path(log_dir=envs.STORAGE_ROOT)))
    client = DataJoinControlClient(args.server_port)
    reader = ExampleIdReader(input_path=args.input_path, file_type=FileType.CSV, key_column=args.key_column)
    writer = ExampleIdWriter(output_path=args.output_path, key_column=args.key_column)
    if args.data_join_type == DataJoinType.HASHED_DATA_JOIN:
        joiner = HashedDataJoiner(joiner_port=args.joiner_port)
    else:
        joiner = OtPsiJoiner(joiner_port=args.joiner_port)
    partition_info = PartitionInfo(args.input_path)
    partition_ids = get_partition_ids(args.worker_rank, args.num_workers, partition_info.num_partitions)
    logging.info(f'allocated partitions {partition_ids} to worker {args.worker_rank}')
    manager = DataJoinManager(joiner, client, reader, writer)
    num_partitions = reader.num_partitions
    if num_partitions == 0:
        logging.info('[run_joiner]num_partitions of client is zero, client close grpc and quit.')
        client.finish()
        return
    ret = wait_for_ready_and_verify(client, num_partitions, args.num_workers)
    if ret:
        manager.run(partition_ids=partition_ids)
        client.close()
    else:
        client.finish()  # Close _stub
        client.close()


def run(args: Arguments):
    logging.config.dictConfig(logging_config(file_path=log_path(log_dir=envs.STORAGE_ROOT)))
    if args.partitioned:
        run_joiner(args)
    else:
        partitioned_path = tempfile.mkdtemp()
        logging.info(f'[DataJoinControlClient] input not partitioned, start partitioning to {partitioned_path}...')
        client = DataJoinControlClient(args.server_port)
        wait_for_ready(client=client)
        parameter_response = client.get_parameter()
        # DataJoinControlClient includes a gRPC channel.
        # Creating a gRPC channel on the same port again may cause error.
        # So the client needs to be closed after use.
        client.close()
        num_partitions = parameter_response.num_partitions
        logging.info(f'[DataJoinControlClient] data will be partitioned to {num_partitions} partition(s).')
        partitioner = Partitioner(input_path=args.input_path,
                                  output_path=partitioned_path,
                                  num_partitions=num_partitions,
                                  block_size=1000000,
                                  key_column=args.key_column,
                                  queue_size=40,
                                  reader_thread_num=20,
                                  writer_thread_num=20)
        partitioner.partition_data()
        logging.info('[DataJoinControlClient] partition finished.')
        futures = []
        pool = ProcessPoolExecutor()
        for worker in range(args.num_workers):
            worker_args = copy.deepcopy(args)
            worker_args.worker_rank = worker
            worker_args.input_path = partitioned_path
            worker_args.server_port = args.server_port + worker * 2
            worker_args.joiner_port = args.joiner_port + worker
            futures.append(pool.submit(run_joiner, worker_args))
        res = wait(futures, return_when=FIRST_EXCEPTION)
        for future in res.done:
            if future.exception():
                # early stop all subprocesses when catch exception
                for pid, process in pool._processes.items():  # pylint: disable=protected-access
                    process.terminate()
                raise Exception('Joiner subprocess failed') from future.exception()

        combine_writer = ExampleIdWriter(output_path=args.output_path, key_column=args.key_column)
        combine_writer.combine(num_partitions)

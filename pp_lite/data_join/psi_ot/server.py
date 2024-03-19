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

import logging
import logging.config

from pp_lite.data_join import envs

from pp_lite.rpc.server import RpcServer
from pp_lite.proto.arguments_pb2 import Arguments
from pp_lite.proto.common_pb2 import FileType, DataJoinType
from pp_lite.data_join.psi_ot.data_join_control_servicer import DataJoinControlServicer
from pp_lite.data_join.psi_ot.data_join_server import DataJoinServer
from pp_lite.data_join.psi_ot.joiner.ot_psi_joiner import OtPsiJoiner
from pp_lite.data_join.psi_ot.joiner.hashed_data_joiner import HashedDataJoiner
from pp_lite.data_join.utils.example_id_writer import ExampleIdWriter
from pp_lite.data_join.utils.example_id_reader import ExampleIdReader
from pp_lite.utils.logging_config import logging_config, log_path


def run(args: Arguments):
    logging.config.dictConfig(logging_config(log_path(log_dir=envs.STORAGE_ROOT)))
    reader = ExampleIdReader(input_path=args.input_path, file_type=FileType.CSV, key_column=args.key_column)
    writer = ExampleIdWriter(output_path=args.output_path, key_column=args.key_column)
    if args.data_join_type == DataJoinType.HASHED_DATA_JOIN:
        joiner = HashedDataJoiner(joiner_port=args.joiner_port)
    else:
        joiner = OtPsiJoiner(joiner_port=args.joiner_port)
    data_join_server = DataJoinServer(joiner, reader=reader, writer=writer)
    servicer = DataJoinControlServicer(data_join_server=data_join_server, cluster_spec=args.cluster_spec)
    server = RpcServer(servicer, listen_port=args.server_port)
    server.start()
    server.wait()
    logging.info('server is finished!')

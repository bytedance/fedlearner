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

from os import getenv
import json
from pp_lite.proto.arguments_pb2 import Arguments
from web_console_v2.inspection.error_code import AreaCode, ErrorType, JobException


def get_arguments() -> Arguments:
    for i in ['INPUT_PATH', 'OUTPUT_PATH', 'KEY_COLUMN', 'SERVER_PORT', 'JOINER_PORT']:
        if getenv(i) is None:
            raise JobException(AreaCode.UNKNOWN, ErrorType.INPUT_PARAMS_ERROR, f'Environment variable {i} is missing.')
    args = Arguments()
    args.input_path = getenv('INPUT_PATH')
    args.output_path = getenv('OUTPUT_PATH')
    args.key_column = getenv('KEY_COLUMN')
    args.server_port = int(getenv('SERVER_PORT'))
    args.joiner_port = int(getenv('JOINER_PORT'))
    args.worker_rank = int(getenv('INDEX', '0'))
    if getenv('NUM_WORKERS'):
        args.num_workers = int(getenv('NUM_WORKERS'))
    role = getenv('ROLE', '')
    if getenv('CLUSTER_SPEC') and role != 'light_client':
        cluster_spec = json.loads(getenv('CLUSTER_SPEC'))

        # Only accept CLUSTER_SPEC in cluster environment,
        # so that CLUSTER_SPEC from .env in light client environment can be omitted.
        if 'clusterSpec' in cluster_spec:
            args.cluster_spec.workers.extend(cluster_spec['clusterSpec']['Worker'])
            args.num_workers = len(args.cluster_spec.workers)
    assert args.num_workers > 0
    return args

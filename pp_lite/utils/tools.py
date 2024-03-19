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
from typing import Dict, List


def print_named_dict(name: str, target_dict: Dict):
    logging.info(f'===================={name}====================')
    for key, value in target_dict.items():
        logging.info(f'{key}: {value}')
    logging.info(f'===================={"=" * len(name)}====================')


def get_partition_ids(worker_rank: int, num_workers: int, num_partitions: int) -> List[int]:
    return [i for i in range(num_partitions) if i % num_workers == worker_rank]

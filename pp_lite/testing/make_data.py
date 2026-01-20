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

import csv
import os
import shutil
from typing import List
import uuid


def _make_fake_data(input_dir: str,
                    num_partitions: int,
                    line_num: int,
                    partitioned: bool = True,
                    spark: bool = False) -> List[str]:
    header = sorted([f'x_{str(i)}' for i in range(20)])
    header.append('part_id')
    header = sorted(header)
    for pid in range(num_partitions):
        filename_prefix = 'part' if partitioned else 'abcd'
        filename = os.path.join(input_dir, f'{filename_prefix}-{pid}')
        if spark:
            filename = filename + '-' + str(uuid.uuid4())
        with open(filename, 'w', encoding='utf-8') as file:
            writer = csv.DictWriter(file, header)
            writer.writeheader()
            for i in range(line_num):
                data = {h: pid + i + j for j, h in enumerate(header)}
                data['part_id'] = pid
                writer.writerow(data)
    if partitioned:
        with open(os.path.join(input_dir, '_SUCCESS'), 'w', encoding='utf-8') as f:
            f.write('')
    return header


def make_data(num_partition, client_path: str, server_path: str):
    shutil.rmtree(client_path, ignore_errors=True)
    shutil.rmtree(server_path, ignore_errors=True)
    os.makedirs(client_path, exist_ok=True)
    os.makedirs(server_path, exist_ok=True)
    num_lines = 1000
    ex_lines = 200
    for part_id in range(num_partition):
        client_range = range(part_id * num_lines * 10, part_id * num_lines * 10 + num_lines)
        server_range = range(part_id * num_lines * 10 - ex_lines, part_id * num_lines * 10 + num_lines - ex_lines)
        client_ids = [{'raw_id': i} for i in client_range]
        server_ids = [{'raw_id': i} for i in server_range]
        with open(os.path.join(client_path, f'part-{part_id}'), 'wt', encoding='utf-8') as f:
            writer = csv.DictWriter(f, ['raw_id'])
            writer.writeheader()
            writer.writerows(client_ids)
        with open(os.path.join(server_path, f'part-{part_id}'), 'wt', encoding='utf-8') as f:
            writer = csv.DictWriter(f, ['raw_id'])
            writer.writeheader()
            writer.writerows(server_ids)


if __name__ == '__main__':
    make_data(2, 'client_input', 'server_input')

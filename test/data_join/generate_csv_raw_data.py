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

import argparse
import logging
import os
from collections import OrderedDict
from cityhash import CityHash32 # pylint: disable=no-name-in-module

from tensorflow.compat.v1 import gfile

from fedlearner.data_join import common
from fedlearner.data_join.rsa_psi.sort_run_merger import SortRunMergerWriter

def generate_input_csv(base_dir, start_id, end_id, partition_num):
    for partition_id in range(partition_num):
        dirpath = os.path.join(base_dir, common.partition_repr(partition_id))
        if not gfile.Exists(dirpath):
            gfile.MakeDirs(dirpath)
        assert gfile.IsDirectory(dirpath)
    csv_writers = [SortRunMergerWriter(base_dir, 0, partition_id)
                   for partition_id in range(partition_num)]
    for idx in range(start_id, end_id):
        if idx % 262144 == 0:
            logging.info("Process at index %d", idx)
        partition_id = CityHash32(str(idx)) % partition_num
        raw = OrderedDict()
        raw['raw_id'] = str(idx)
        raw['feat_0'] = str((partition_id << 30) + 0) + str(idx)
        raw['feat_1'] = str((partition_id << 30) + 1) + str(idx)
        raw['feat_2'] = str((partition_id << 30) + 2) + str(idx)
        csv_writers[partition_id].append(raw)
    for partition_id, csv_writer in enumerate(csv_writers):
        fpaths = csv_writer.finish()
        logging.info("partition %d dump %d files", partition_id, len(fpaths))
        for seq_id, fpath in enumerate(fpaths):
            logging.info("  %d. %s", seq_id, fpath)
        logging.info("---------------")

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    logging.basicConfig(format='%(asctime)s %(message)s')
    parser = argparse.ArgumentParser(description='csv raw data generator cmd.')
    parser.add_argument('--base_dir', type=str, required=True,
                        help='the base dir of fs to store the generated csv file')
    parser.add_argument('--partition_num', type=int, required=True,
                        help='the partition num of generated data')
    parser.add_argument('--start_id', type=int, required=True,
                        help='the start id of generated csv file')
    parser.add_argument('--end_id', type=int, required=True,
                        help='the end id of generated csv file')
    args = parser.parse_args()
    generate_input_csv(args.base_dir, args.start_id,
                       args.end_id, args.partition_num)

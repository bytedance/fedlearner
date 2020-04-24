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

import sys
import os
import subprocess
import argparse
import logging

def main():
    logging.getLogger().setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser(description='All unit test for data join')
    parser.add_argument('--test_dir', type=str, default='./test',
                        help='the directory of unit test')
    args = parser.parse_args()
    test_scripts = [
            'test_etcd_client.py',
            'test_raw_data_manifest_manager.py',
            'test_raw_data_visitor.py',
            'test_compressed_raw_data_visitor.py',
            'test_dumped_example_id.py',
            'test_data_block_manager.py',
            'test_data_block_dumper.py',
            'test_example_join.py',
            'test_data_join_master.py',
            'test_data_join_worker.py',
            'test_data_block_visitor.py',
            'test_data_join_portal.py'
    ]

    for script in test_scripts:
        logging.info("Executing {}".format(script))
        proc = subprocess.Popen(['python', os.path.join(args.test_dir, script)])
        if proc.wait() == 0:
            logging.info("test {} OK".format(script))
        else:
            logging.fatal("test {} Error".format(script))
            sys.exit(1)

if __name__ == '__main__':
    main()

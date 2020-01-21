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

def parse_arguments():
    parser = argparse.ArgumentParser(description='ByteFL Trainer.')
    parser.add_argument('local_addr', type=str,
                        help='Listen address of the local bridge, ' \
                             'in [IP]:[PORT] format')
    parser.add_argument('peer_addr', type=str,
                        help='Address of peer\'s bridge, ' \
                             'in [IP]:[PORT] format')
    parser.add_argument('master_addr', type=str, default=None,
                        help='Address of trainer master, ' \
                             'in [IP]:[PORT] format. ' \
                             'Use local master for  if set to None.')

    args = parser.parse_args()


def train():
    pass

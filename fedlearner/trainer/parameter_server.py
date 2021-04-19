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
# pylint: disable=unused-import

import logging
import argparse
import signal

import tensorflow.compat.v1 as tf
from fedlearner.trainer.cluster_server import ClusterServer

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='FedLearner Parameter Server.')
    parser.add_argument('address', type=str,
                        help='Listen address of the parameter server, ' \
                             'with format [IP]:[PORT]')
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)-15s [%(filename)s:%(lineno)d] " \
               "%(levelname)s : %(message)s")
    args = parser.parse_args()

    cluster_spec = tf.train.ClusterSpec({'ps': {0: args.address}})
    cluster_server = ClusterServer(cluster_spec, "ps")

    sig = signal.sigwait([signal.SIGHUP, signal.SIGINT, signal.SIGTERM])
    logging.info("Server shutdown by signal: %s", signal.Signals(sig).name)

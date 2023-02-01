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
from click import group

from envs import Envs

from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.hooks import pre_start_hook
from fedlearner_webconsole.composer.composer import composer
from fedlearner_webconsole.rpc.server import rpc_server
from fedlearner_webconsole.k8s.k8s_watcher import k8s_watcher


@group('entrypoint')
def entrypoint():
    pass


@entrypoint.command('start-rpc')
def start_rpc():
    logging.info('Starting Rpc...')
    # Start k8s watcher in rpc server process for now.
    k8s_watcher.start()
    rpc_server.stop()
    rpc_server.start(Envs.GRPC_LISTEN_PORT)
    rpc_server.wait_for_termination()


@entrypoint.command('start-composer')
def start_composer():
    # TODO(wangsen.0914): refactor logging_config
    # There's a race condition when multiple process logging to same file.
    logging.basicConfig(level=logging.DEBUG)
    logging.info('Starting composer...')
    composer.run(db.engine)
    composer.wait_for_termination()


if __name__ == '__main__':
    pre_start_hook()
    entrypoint()

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

#!/bin/bash
set -e

# This script is designed for triggering by bazel run.
# So it can be only executed in root of our workspace.
[[ ! ${PWD} =~ .*privacy_computing_platform ]] && echo "this scripts should be executed in root of workspace"; exit 1;

function flask_command {
    FLASK_APP=web_console_v2/api/command:app \
    APM_SERVER_ENDPOINT=/dev/null \
    web_console_v2/api/cmds/flask_cli_bin \
    $*
}

export SYSTEM_INFO="{\"domain_name\": \"dev.fedlearner.net\", \"name\": \"Dev\"}"
export APM_SERVER_ENDPOINT=stdout
export FLASK_ENV=development

# set runtime env
source web_console_v2/api/cmds/runtime_env.sh

# Migrates DB schemas
flask_command create-db
# Loads initial data
flask_command create-initial-data
# Runs Api Composer and gRPC service
web_console_v2/api/cmds/supervisord_cli_bin \
    -c web_console_v2/api/cmds/supervisord_dev.conf --nodaemon

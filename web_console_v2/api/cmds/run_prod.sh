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

# Add hook into pythonpath
export PYTHONPATH=$PYTHONPATH:$PWD
# We should find if $0.runfiles exists which is runtime files exists.
[[ -d "$0.runfiles" ]] && cd $0.runfiles/privacy_computing_platform

# link all deps inside runfiles to $workspace/external
if [[ ! -d "external" ]]
then
  echo "linking symbolic into external..."
  mkdir external
  ls ../ | grep -v privacy_computing_platform | xargs -IX ln -s $PWD/../X $PWD/external/X
fi

function flask_command {
    FLASK_APP=web_console_v2/api/command:app \
    APM_SERVER_ENDPOINT=/dev/null \
    web_console_v2/api/cmds/flask_cli_bin \
    $*
}

# set runtime env
source web_console_v2/api/cmds/runtime_env.sh

# Configure ElasticSearch ILM Information
flask_command es-configuration

# Iterates arguments
while test $# -gt 0
do
    case "$1" in
        --migrate)
            echo "Migrating DB"
            # Migrates DB schemas
            flask_command db upgrade \
                --directory web_console_v2/api/migrations
            ;;
    esac
    shift
done

flask_command create-initial-data

export FEDLEARNER_WEBCONSOLE_LOG_DIR=/var/log/fedlearner_webconsole/
mkdir -p $FEDLEARNER_WEBCONSOLE_LOG_DIR

# This starts supervisor daemon which will start all processes defined in
# supervisord.conf. The daemon starts in background by default.
web_console_v2/api/cmds/supervisord_cli_bin \
    -c web_console_v2/api/cmds/supervisord.conf
# This tails logs from all processes defined in supervisord.conf.
# The purpose for this is to put supervisor to foreground so that the
# pod/container will not be terminated.
web_console_v2/api/cmds/supervisorctl_cli_bin \
    -c web_console_v2/api/cmds/supervisord.conf maintail -f

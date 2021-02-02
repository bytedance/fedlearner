#!/bin/bash
#
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

set -e

# Adds root directory to python path to make the modules findable.
ROOT_DIRECTORY=$(dirname "$0")
export PYTHONPATH=$PYTHONPATH:"$ROOT_DIRECTORY"

# Iterates arguments
while test $# -gt 0
do
    case "$1" in
        --migrate)
            echo "Migrating DB"
            export FLASK_APP=manage:app
            # Migrates DB schemas
            flask db upgrade
            ;;
    esac
    shift
done

# Loads initial data
flask create-initial-data

gunicorn manage:app \
    --config="$ROOT_DIRECTORY/gunicorn_config.py"

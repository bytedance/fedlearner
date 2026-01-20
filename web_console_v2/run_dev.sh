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

# Whether API or Client, always start nginx
diff_result=$(diff ../tools/dev_workspace/nginx.conf /etc/nginx/conf.d/nginx.conf || true)
if [[ $diff_result != '' ]]
then
    echo "detect difference, restarting nginx"
    cp -f ../tools/dev_workspace/nginx.conf /etc/nginx/conf.d/nginx.conf
    service nginx restart
fi

if [[ $ROLE == client ]]
then
    # Starts Client server
    cd ./client
    npm install -g pnpm@6.4.0 && pnpm install && PORT=3000 pnpm run start
elif [[ $ROLE == api ]]
then
    # Starts API server
    cd ./api
    bash run_dev.sh
else
    echo "Invalid ROLE: $ROLE"
fi

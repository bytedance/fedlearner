#!/bin/bash
#
# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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

if ! type coverage &> /dev/null ; then
  echo "coverage is not found, please install it by \`pip3 install coverage\`"
  exit 1
fi

# Removes old coverage data
coverage erase
for file in $(find test -type f); do
  if [[ $file =~ .*_test\.py$ ]]; then
    coverage run "$file"
  fi
done
coverage combine
coverage html

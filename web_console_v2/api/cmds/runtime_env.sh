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

# Adds root directory to python path to make the modules findable.
export PYTHONPATH=$PYTHONPATH:"web_console_v2/api/"

# disable pymalloc to avoid high memory usage when parrallism allocation small objects
# Ref: https://docs.python.org/3/c-api/memory.html#the-pymalloc-allocator
export PYTHONMALLOC=malloc
export PYTHONUNBUFFERED=1

# When recongize HADOOP_HOME, export some also useful environment variables for GFile
if [ ! -z $HADOOP_HOME ]
then
    echo "set hadoop env"
    # This is super import for compitable with hadoop and hadoop_current
    if [ -f "$HADOOP_HOME/conf/hadoop-env.sh" ]
    then
        export HADOOP_CONF_DIR=$HADOOP_HOME/conf
        source "$HADOOP_HOME/conf/hadoop-env.sh" &> /dev/null
    else
        export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop 
        source "$HADOOP_HOME/etc/hadoop/hadoop-env.sh" &> /dev/null
    fi
    export LD_LIBRARY_PATH=${HADOOP_HOME}/lib/native:${HADOOP_HOME}/lib/native/nfs:${JAVA_HOME}/jre/lib/amd64/server:${LD_LIBRARY_PATH}
    export CLASSPATH=$($HADOOP_HOME/bin/hadoop classpath --glob)
fi

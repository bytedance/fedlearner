#!/bin/bash
#
# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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

PORT=33600

docker rm -f mysql-fedlearner &> /dev/null
docker run -it --name mysql-fedlearner -p $PORT:3306 --rm -d -e MYSQL_ROOT_PASSWORD=root mysql:5.7 --default-authentication-plugin=mysql_native_password

while :
do
    mysql -h 0.0.0.0 --port 33600 -uroot -proot -e "CREATE DATABASE IF NOT EXISTS fedlearner;" &> /dev/null
	if [ $? -eq 0 ]
	then
		break
	fi
done


echo URI: mysql+pymysql://root:root@localhost:$PORT/fedlearner
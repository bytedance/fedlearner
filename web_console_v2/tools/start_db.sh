#! /bin/bash
PORT=33600

docker rm -f mysql-fedlearner &> /dev/null
docker run -it --name mysql-fedlearner -p $PORT:3306 --rm -d -e MYSQL_ROOT_PASSWORD=root mysql:8 --default-authentication-plugin=mysql_native_password

while :
do
    mysql -h 0.0.0.0 --port 33600 -uroot -proot -e "CREATE DATABASE IF NOT EXISTS fedlearner;" &> /dev/null
	if [ $? -eq 0 ]
	then
		break
	fi
done


echo URI: mysql+pymysql://root:root@localhost:$PORT/fedlearner
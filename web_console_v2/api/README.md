# Code for BE API

## Prerequisites

* GNU Make
* Python3

## Get started
```
python3 -m venv <a folder for virtual env>
source <a folder for virtual env>/bin/activate
pip3 install -r requirements.txt

# Generates python code for proto
make protobuf

# Creates schemas for DB
FLASK_APP=command:app flask db upgrade

# Creates initial user
FLASK_APP=command:app flask create-initial-data

# Starts the server
export FLASK_ENV=development
flask run
```

## Create a table for flapp worker
```
CREATE TABLE `datasource_meta` (
	`id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'row id',
	`kv_key` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL COMMENT 'key for kv store',
	`kv_value` longtext CHARACTER SET utf8 COLLATE utf8_general_ci NULL COMMENT 'value for kv store',
	PRIMARY KEY (`id`),
	Unique KEY `kv_key`(`kv_key`) USING BTREE
) ENGINE=InnoDB
DEFAULT CHARACTER SET=utf8 COLLATE=utf8_general_ci
AUTO_INCREMENT=74
ROW_FORMAT=DYNAMIC
AVG_ROW_LENGTH=4096;
```


### Unit tests
```
cd <root folder of API>
make unit-test
```

## Helpers
### Gets all routes
```
FLASK_APP=command:app flask routes
```
### Update migration files
delete migrations folder first
```

FLASK_APP=command:app flask db init
FLASK_APP=command:app flask flask db migrate -m "Initial migration."
```

## References

### Default date time in sqlalchemy
https://stackoverflow.com/questions/13370317/sqlalchemy-default-datetime/33532154#33532154

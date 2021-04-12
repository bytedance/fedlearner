# Code for BE API

## Prerequisites

* GNU Make
* Python3
* MySQL 8.0

## Get started

```
python3 -m venv <a folder for virtual env>
source <a folder for virtual env>/bin/activate
pip3 install -r requirements.txt

# Generates python code for proto
make protobuf

# Use MySQL, please create database in advance, then set 
# SQLALCHEMY_DATABASE_URI, for example as follows
export SQLALCHEMY_DATABASE_URI=mysql+pymysql://root:root@localhost:33600/fedlearner

# Creates schemas for DB
FLASK_APP=command:app flask db upgrade

# Creates initial user
FLASK_APP=command:app flask create-initial-data

# Starts the server
export FLASK_ENV=development
flask run
```

## Tests

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

### Add migration files

```
FLASK_APP=command:app flask db migrate -m "Whats' changed"
# like dry-run mode, preview auto-generated SQL
FLASK_APP=command:app flask db upgrade --sql
# update database actually
FLASK_APP=command:app flask db upgrade
```

### Reset migration files

Delete migrations folder first.
```
FLASK_APP=command:app flask db init
FLASK_APP=command:app flask db migrate -m "Initial migration."
```

## [Style guide](docs/style_guide.md)
## [Best practices](docs/best_practices.md)

## References

### Default date time in sqlalchemy
https://stackoverflow.com/questions/13370317/sqlalchemy-default-datetime/33532154#33532154

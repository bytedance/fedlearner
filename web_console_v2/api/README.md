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
### Update migration files
delete migrations folder first
```

FLASK_APP=command:app flask db init
FLASK_APP=command:app flask db migrate -m "Initial migration."
```

## References

### Default date time in sqlalchemy
https://stackoverflow.com/questions/13370317/sqlalchemy-default-datetime/33532154#33532154

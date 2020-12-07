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

export FLASK_APP=manage:app

# Creates schemas for DB
flask db upgrade

# Creates initial user
flask create-db

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
export FLASK_APP=manage:app
flask routes
```

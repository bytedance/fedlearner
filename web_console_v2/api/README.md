# Code for BE API

## Prerequisites

* GNU Make
* Python3

## Get started
```
python3 -m venv <a folder for virtual env>
pip3 install -r requirements.txt

# Generates python code for proto
make protobuf

# Creates schemas for DB
flask db upgrade

# Creates initial user
flask create-db
```

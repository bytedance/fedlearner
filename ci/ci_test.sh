#!/bin/bash
set -ex

export PYTHONPATH=$(PWD):$(PYTHONPATH)

git submodule update --init
pip install -r requirements.txt

make protobuf
make lint
make test

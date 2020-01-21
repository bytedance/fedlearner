#!/bin/bash
set -ex

export PYTHONPATH=$(PWD):$(PYTHONPATH)

git submodule update --init
pip install -i http://mirrors.aliyun.com/pypi/simple -r requirements.txt

make protobuf
# make lint
# make test

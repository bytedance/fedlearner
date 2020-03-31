#!/bin/bash
set -ex

export PYTHONPATH=$(PWD):$(PYTHONPATH)

git submodule update --init
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

make op
make protobuf
make lint
make test

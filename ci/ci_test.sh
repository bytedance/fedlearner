#!/bin/bash
set -ex

export PYTHONPATH=${PWD}:${PYTHONPATH}

make op
make protobuf
make lint
make test

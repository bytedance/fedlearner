#!/bin/bash
set -ex

BASE_DIR=`dirname $0`
cd $BASE_DIR

export CUDA_VISIBLE_DEVICES=""

rm -rf data model

python make_data.py

python leader.py --local-addr=localhost:50051 \
                 --peer-addr=localhost:50052 \
                 --data-path=data/leader \
                 --save-checkpoint-steps=200 \
                 --checkpoint-path=model/leader/checkpoint \
                 --export-path=model/leader/saved_model \
                 --epoch-num=5 &

python follower.py --local-addr=localhost:50052 \
                   --peer-addr=localhost:50051 \
                   --data-path=data/follower/ \
                   --save-checkpoint-steps=200 \
                   --checkpoint-path=model/follower/checkpoint \
                   --export-path=model/follower/saved_model

wait

rm -rf data model
echo "test done"

#!/bin/bash
set -ex

export CUDA_VISIBLE_DEVICES=""

BASE_DIR=`dirname $0`
cd $BASE_DIR

rm -rf data model

python make_data.py

python leader.py --local-addr=localhost:50010 \
                 --peer-addr=localhost:50011 \
                 --data-path=data/leader \
                 --save-checkpoint-steps=200 \
                 --checkpoint-path=model/leader/checkpoint \
                 --export-path=model/leader/saved_model \
                 --epoch-num=3 &

python follower.py --local-addr=localhost:50011 \
                 --peer-addr=localhost:50010 \
                 --data-path=data/follower \
                 --checkpoint-path=model/follower/checkpoint \
                 --save-checkpoint-steps=200 \
                 --export-path=model/follower/saved_model

wait

rm -rf data model
echo "test done"
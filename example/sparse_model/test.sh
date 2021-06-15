#!/bin/bash
set -ex

BASE_DIR=`dirname $0`
cd $BASE_DIR

rm -rf data model

export CUDA_VISIBLE_DEVICES=""

python make_data.py --fid_version=1
python follower.py --local-addr=localhost:50010 \
                   --peer-addr=localhost:50011 \
                   --data-path=data/follower/ \
                   --checkpoint-path=model/follower \
                   --save-checkpoint-steps=200 \
                   --export-path=model/follower/saved_model \
                   --epoch-num=5 \
                   --sparse-estimator=True &

python leader.py   --local-addr=localhost:50011 \
                   --peer-addr=localhost:50010 \
                   --data-path=data/leader/ \
                   --checkpoint-path=model/leader \
                   --save-checkpoint-steps=200 \
                   --export-path=model/leader/saved_model \
                   --sparse-estimator=True 

wait

rm -rf data model
python make_data.py --fid_version=2
python follower.py --local-addr=localhost:50010 \
                   --peer-addr=localhost:50011 \
                   --data-path=data/follower/ \
                   --checkpoint-path=model/follower \
                   --save-checkpoint-steps=100 \
                   --export-path=model/follower/saved_model \
                   --epoch-num=5 \
                   --sparse-estimator=True \
                   --fid_version=2 &

python leader.py   --local-addr=localhost:50011 \
                   --peer-addr=localhost:50010 \
                   --data-path=data/leader/ \
                   --checkpoint-path=model/leader \
                   --save-checkpoint-steps=100 \
                   --export-path=model/leader/saved_model \
                   --sparse-estimator=True \
                   --fid_version=2

wait

rm -rf data model
echo "test done"

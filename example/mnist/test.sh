#!/bin/bash
export CUDA_VISIBLE_DEVICES=""

python make_data.py

python leader.py --local-addr=localhost:50051     \
                 --peer-addr=localhost:50052      \
                 --data-path=data/leader          \
                 --checkpoint-path=log/leader/checkpoint \
                 --export-path=log/leader/export         \
                 --save-checkpoint-steps=10       \
                 --summary-save-steps=10          \
                 --epoch-num=1                  \
                 --export-model=false & # not export model

python follower.py --local-addr=localhost:50052     \
                   --peer-addr=localhost:50051      \
                   --data-path=data/follower/       \
                   --checkpoint-path=log/follower/checkpoint \
                   --export-path=log/follower/export \
                   --save-checkpoint-steps=10       \
                   --summary-save-steps=10          \
                   --epoch-num=1                   \
                   --export-model=true # export model

wait

rm -rf data log
echo "test done"

#!/bin/bash
export CUDA_VISIBLE_DEVICES=""

python follower.py --local-addr=localhost:40012 \
                   --peer-addr=localhost:40002 \
                   --worker-rank=0 \
                   --data-path=data/follower/ \
                   --checkpoint-path=model/follower \
                   --save-checkpoint-steps=100 \
                   --export-path=model/follower/saved_model

#!/bin/bash
export CUDA_VISIBLE_DEVICES=""


ROLE=$1

if [ "$ROLE" == "leader" ]; then
    python leader.py --local-addr=localhost:50010 \
                     --peer-addr=localhost:50011 \
                     --worker-rank=0 \
                     --data-path=data/leader/ \
                     --checkpoint-path=model/leader \
                     --save-checkpoint-steps=100 \
                     --export-path=model/leader/saved_model 
elif [ "$ROLE" == "follower" ]; then
    python follower.py --local-addr=localhost:50011 \
                       --peer-addr=localhost:50010 \
                       --worker-rank=0 \
                       --data-path=data/follower/ \
                       --checkpoint-path=model/follower \
                       --save-checkpoint-steps=100 \
                       --export-path=model/follower/saved_model
else
    echo "usage: $0 [leader | follower]"    
fi
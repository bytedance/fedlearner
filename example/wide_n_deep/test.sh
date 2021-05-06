#!/bin/bash
export CUDA_VISIBLE_DEVICES=""


ROLE=$1

if [ "$ROLE" == "leader" ]; then
    python leader.py --local-addr=localhost:50010 \
                     --peer-addr=localhost:50011 \
                     --data-path=data/leader \
                     --checkpoint-path=model/leader/checkpoint \
                     --export-path=model/leader/saved_model \
                     --epoch-num=3 \
                     --loglevel=info

elif [ "$ROLE" == "follower" ]; then
    python follower.py --local-addr=localhost:50011 \
                       --peer-addr=localhost:50010 \
                       --data-path=data/follower \
                       --checkpoint-path=model/follower/checkpoint \
                       --save-checkpoint-steps=100 \
                       --export-path=model/follower/saved_model \
                       --loglevel=info

else
    echo "usage: $0 [leader | follower]"    
fi

#!/bin/bash
export CUDA_VISIBLE_DEVICES=""

BASH_DIR=`dirname $0`

ROLE=$1

if [ "$ROLE" == "leader" ]; then
    python $BASH_DIR/leader.py --local-addr=localhost:50010 \
                               --peer-addr=localhost:50011 \
                               --data-path=$BASH_DIR/data/leader \
                               --checkpoint-path=$BASH_DIR/model/leader/checkpoint \
                               --export-path=$BASH_DIR/model/leader/saved_model \
                               --epoch-num=3

elif [ "$ROLE" == "follower" ]; then
    python $BASH_DIR/follower.py --local-addr=localhost:50011 \
                                 --peer-addr=localhost:50010 \
                                 --data-path=$BASH_DIR/data/follower \
                                 --checkpoint-path=$BASH_DIR/model/follower/checkpoint \
                                 --save-checkpoint-steps=100 \
                                 --export-path=$BASH_DIR/model/follower/saved_model

else
    echo "usage: $0 [leader | follower]"    
fi
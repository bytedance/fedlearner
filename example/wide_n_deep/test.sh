#!/bin/bash
export CUDA_VISIBLE_DEVICES=""


ROLE=$1

if [ "$ROLE" == "leader" ]; then
    python leader.py --local-addr=localhost:50010 \
                     --peer-addr=localhost:50011 \
                     --worker-rank=0 \
                     --data-path=data/leader/ \
                     --checkpoint-path=model/leader/checkpoint \
                     --save-checkpoint-steps=100 \
                     --export-path=model/leader/saved_model \
                     --verbosity=2 \
                     --load-checkpoint-filename-with-path=model/leader/checkpoint/complete_checkpoint/fl-complete-model.ckpt-1615915510

elif [ "$ROLE" == "follower" ]; then
    python follower.py --local-addr=localhost:50011 \
                       --peer-addr=localhost:50010 \
                       --worker-rank=0 \
                       --data-path=data/follower/ \
                       --checkpoint-path=model/follower/checkpoint \
                       --save-checkpoint-steps=100 \
                       --export-path=model/follower/saved_model \
                       --verbosity=2 \
                       --load-checkpoint-filename-with-path=model/follower/checkpoint/complete_checkpoint/fl-complete-model.ckpt-1615915510

else
    echo "usage: $0 [leader | follower]"    
fi

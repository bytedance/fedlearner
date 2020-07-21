#!/bin/bash
export PYTHONPATH=/home/dev/fedlearner
export CUDA_VISIBLE_DEVICES=""
python follower.py --local-addr=localhost:50010 \
                   --peer-addr=localhost:50011 \
                   --worker-rank=0 \
                   --data-path=data/follower/ \
                   --checkpoint-path=model/follower \
                   --save-checkpoint-steps=100 \
                   --export-path=model/follower/saved_model \
                   --sparse-estimator=True >follower.log 2>&1 &
follower_pid=`echo $!`

python leader.py   --local-addr=localhost:50011 \
                   --peer-addr=localhost:50010 \
                   --worker-rank=0 \
                   --data-path=data/leader/ \
                   --checkpoint-path=model/leader \
                   --save-checkpoint-steps=100 \
                   --export-path=model/leader/saved_model \
                   --sparse-estimator=True >leader.log 2>&1 &
leader_pid=`echo $!`
wait ${follower_pid}
wait ${leader_pid}

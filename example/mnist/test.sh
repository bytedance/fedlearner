#!/bin/bash
export CUDA_VISIBLE_DEVICES=""

python make_data.py

python leader.py --local-addr=localhost:50051     \
                 --peer-addr=localhost:50052      \
                 --data-path=data/leader          \
		 --checkpoint-path=log/checkpoint \
		 --save-checkpoint-steps=10 &

python follower.py --local-addr=localhost:50052     \
                   --peer-addr=localhost:50051      \
                   --data-path=data/follower/       \
		   --checkpoint-path=log/checkpoint \
		   --save-checkpoint-steps=10

wait

rm -rf data log
echo "test done"

#!/bin/bash

set -e

date
export CUDA_VISIBLE_DEVICES=""

rm -rf model # data

#python make_data.py

unset http_proxy https_proxy
env

python -m fedlearner.trainer.parameter_server localhost:40051 & 
python -u leader.py --local-addr=localhost:50051                       \
                    --peer-addr=localhost:50052                    \
                    --data-path=data/leader                            \
                    --checkpoint-path=model/leader/checkpoint          \
                    --export-path=model/leader/saved_model             \
                    --save-checkpoint-steps=10                         \
                    --epoch-num=2                                      \
                    --cluster-spec='{"clusterSpec":{"PS":["localhost:40051"]}}'          \
                    --loglevel=debug &

sleep 5s

python -m fedlearner.trainer.parameter_server localhost:40061 & 
python -u follower.py --local-addr=localhost:50052                     \
                      --peer-addr=localhost:50051                      \
                      --data-path=data/follower                        \
                      --checkpoint-path=model/follower/checkpoint      \
                      --export-path=model/follower/saved_model         \
                      --save-checkpoint-steps=10                       \
                      --epoch-num=2                                    \
                      --cluster-spec='{"clusterSpec":{"PS":["localhost:40061"]}}'          \
                      --loglevel=debug &

wait
echo "test done"

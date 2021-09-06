#!/bin/bash

set -e

export CUDA_VISIBLE_DEVICES=""

rm -rf model # data

#python make_data.py

unset http_proxy https_proxy

python -u leader.py --local-addr=localhost:50051                       \
                    --peer-addr=localhost:50052                        \
                    --data-path=data/leader                            \
                    --checkpoint-path=model/leader/checkpoint          \
                    --export-path=model/leader/saved_model             \
                    --save-checkpoint-steps=10                         \
                    --epoch-num=2                                      \
                    --loglevel=info &

sleep 5s

python -u follower.py --local-addr=localhost:50052                     \
                      --peer-addr=localhost:50051                      \
                      --data-path=data/follower                        \
                      --checkpoint-path=model/follower/checkpoint      \
                      --export-path=model/follower/saved_model         \
                      --save-checkpoint-steps=10                       \
                      --epoch-num=2                                    \
                      --loglevel=info &

wait
echo "test done"

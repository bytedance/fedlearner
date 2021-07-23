#!/bin/bash

set -e

export CUDA_VISIBLE_DEVICES=""

rm -rf model # data

python make_data.py

unset http_proxy https_proxy

export CERT_BASE_DIR=`pwd -P`/xxx/pa
python -u leader.py --local-addr=pa.com:50051                          \
                    --peer-addr=pb.com:50052                           \
                    --data-path=data/leader                            \
                    --checkpoint-path=model/leader/checkpoint          \
                    --export-path=model/leader/saved_model             \
                    --save-checkpoint-steps=10                         \
                    --epoch_num=2 &

sleep 5s

export CERT_BASE_DIR=`pwd -P`/xxx/pb
python -u follower.py --local-addr=pb.com:50052                        \
                      --peer-addr=pa.com:50051                         \
                      --data-path=data/follower                        \
                      --checkpoint-path=model/follower/checkpoint      \
                      --export-path=model/follower/saved_model         \
                      --save-checkpoint-steps=10                       \
                      --epoch_num=2 &

wait
echo "test done"

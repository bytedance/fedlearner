#!/bin/bash

set -ex

cd "$( dirname "${BASH_SOURCE[0]}" )"

rm -rf exp data

python make_data.py --verify-example-ids=1 --dataset=iris --output-type=tfrecord

python -m fedlearner.model.tree.trainer follower \
    --verbosity=1 \
    --local-addr=localhost:50052 \
    --peer-addr=localhost:50051 \
    --verify-example-ids=true \
    --file-ext=.tfrecord \
    --file-wildcard=*tfrecord \
    --file-type=tfrecord \
    --data-path=data/follower_train.tfrecord \
    --validation-data-path=data/follower_test \
    --checkpoint-path=exp/follower_checkpoints \
    --cat-fields=f00001 \
    --output-path=exp/follower_train_output.output &

python -m fedlearner.model.tree.trainer leader \
    --verbosity=1 \
    --local-addr=localhost:50051 \
    --peer-addr=localhost:50052 \
    --verify-example-ids=true \
    --file-ext=.tfrecord \
    --file-wildcard=*tfrecord \
    --file-type=tfrecord \
    --data-path=data/leader_train.tfrecord \
    --validation-data-path=data/leader_test \
    --checkpoint-path=exp/leader_checkpoints \
    --cat-fields=f00001 \
    --output-path=exp/leader_train_output.output

wait

python -m fedlearner.model.tree.trainer leader \
    --verbosity=1 \
    --local-addr=localhost:50051 \
    --peer-addr=localhost:50052 \
    --mode=test \
    --verify-example-ids=true \
    --file-type=tfrecord \
    --file-ext=.tfrecord \
    --file-wildcard=*tfrecord \
    --data-path=data/leader_test/ \
    --cat-fields=f00001 \
    --load-model-path=exp/leader_checkpoints/checkpoint-0004.proto \
    --output-path=exp/leader_test_output &

python -m fedlearner.model.tree.trainer follower \
    --verbosity=1 \
    --local-addr=localhost:50052 \
    --peer-addr=localhost:50051 \
    --mode=test \
    --verify-example-ids=true \
    --file-type=tfrecord \
    --file-ext=.tfrecord \
    --file-wildcard=*tfrecord \
    --data-path=data/follower_test/ \
    --cat-fields=f00001 \
    --load-model-path=exp/follower_checkpoints/checkpoint-0004.proto \
    --output-path=exp/follower_test_output

wait


rm -rf exp data

python make_data.py --dataset=iris --verify-example-ids=1 --output-type=csv

python -m fedlearner.model.tree.trainer follower \
    --verbosity=1 \
    --local-addr=localhost:50052 \
    --peer-addr=localhost:50051 \
    --file-ext=.csv \
    --file-type=csv \
    --file-wildcard=*csv \
    --data-path=data/follower_train.csv \
    --cat-fields=f00001 \
    --checkpoint-path=exp/follower_checkpoints \
    --output-path=exp/follower_train_output.output &

python -m fedlearner.model.tree.trainer leader \
    --verbosity=1 \
    --local-addr=localhost:50051 \
    --peer-addr=localhost:50052 \
    --file-ext=.csv \
    --file-type=csv \
    --file-wildcard=*csv \
    --data-path=data/leader_train.csv \
    --ignore-fields=f00000,f00001 \
    --checkpoint-path=exp/leader_checkpoints \
    --output-path=exp/leader_train_output.output

wait

python -m fedlearner.model.tree.trainer follower \
    --verbosity=2 \
    --local-addr=localhost:50052 \
    --peer-addr=localhost:50051 \
    --mode=test \
    --file-ext=.csv \
    --file-wildcard=*csv \
    --file-type=csv \
    --data-path=data/follower_test/ \
    --cat-fields=f00001 \
    --load-model-path=exp/follower_checkpoints/checkpoint-0004.proto \
    --output-path=exp/follower_test_output &

python -m fedlearner.model.tree.trainer leader \
    --verbosity=2 \
    --local-addr=localhost:50051 \
    --peer-addr=localhost:50052 \
    --mode=test \
    --file-ext=.csv \
    --file-wildcard=*csv \
    --no-data=true \
    --load-model-path=exp/leader_checkpoints/checkpoint-0004.proto \
    --output-path=exp/leader_test_output

wait

python merge_scores.py \
    --left-data-path=data/follower_test/ \
    --left-file-ext=.csv \
    --left-select-fields=example_id \
    --right-data-path=exp/leader_test_output \
    --right-file-ext=.output \
    --right-select-fields=prediction \
    --output-path=exp/merge_output

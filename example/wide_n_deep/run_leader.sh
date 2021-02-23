#!/bin/bash
export CUDA_VISIBLE_DEVICES=""

python leader.py   --local-addr=localhost:40011 \
                   --peer-addr=localhost:40001 \
                   --worker-rank=0 \
                   --data-path=data/leader/ \
                   --checkpoint-path=model/leader \
                   --save-checkpoint-steps=100 \
                   --export-path=model/leader/saved_model

#!/bin/bash

cd "$( dirname "${BASH_SOURCE[0]}" )"
rm -rf data model

export CUDA_VISIBLE_DEVICES=""
set -e

rm -rf data model
python make_data.py --fid_version=2
python leader.py   --local-addr=localhost:50011 \
                   --local-worker \
                   --data-path=data/leader/ \
                   --checkpoint-path=model/leader \
                   --save-checkpoint-steps=100 \
                   --export-path=model/leader/saved_model \
                   --sparse-estimator=True \
                   --fid_version=2
rm -rf data model

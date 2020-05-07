rm -rf exp

python -m fedlearner.model.tree.trainer follower \
    --verbosity=1 \
    --local-addr=localhost:50052 \
    --peer-addr=localhost:50051 \
    --verify-example-ids=true \
    --data-path=data/follower_train.csv \
    --validation-data-path=data/follower_test.csv \
    --checkpoint-path=exp/follower_checkpoints \
    --output-path=exp/follower_output.csv &

python -m fedlearner.model.tree.trainer leader \
    --verbosity=1 \
    --local-addr=localhost:50051 \
    --peer-addr=localhost:50052 \
    --verify-example-ids=true \
    --data-path=data/leader_train.csv \
    --validation-data-path=data/leader_test.csv \
    --checkpoint-path=exp/leader_checkpoints \
    --output-path=exp/leader_output.csv

wait

python -m fedlearner.model.tree.trainer follower \
    --verbosity=1 \
    --local-addr=localhost:50052 \
    --peer-addr=localhost:50051 \
    --mode=test \
    --verify-example-ids=true \
    --data-path=data/follower_test.csv \
    --load-model-path=exp/follower_checkpoints/checkpoint-0004.proto \
    --output-path=exp/follower_test_output.csv &

python -m fedlearner.model.tree.trainer leader \
    --verbosity=1 \
    --local-addr=localhost:50051 \
    --peer-addr=localhost:50052 \
    --mode=test \
    --verify-example-ids=true \
    --data-path=data/leader_test.csv \
    --load-model-path=exp/leader_checkpoints/checkpoint-0004.proto \
    --output-path=exp/leader_test_output.csv

wait

# Federated GBDT Example

This example use two-party federated GBDT algorithms to classify MNIST digits.

To run the the example first prepare the data with:
```
python make_data.py
```
This will generate files in `data`.

Run the following command to start leader:
```
python -m fedlearner.model.tree.trainer leader --local-addr=localhost:50051 --peer-addr=localhost:50052 --data-path=data/leader_train.csv --application-id=test --verbosity=3
```

Run the following command in another terminal session to start follower:
```
python -m fedlearner.model.tree.trainer follower --local-addr=localhost:50052 --peer-addr=localhost:50051 --data-path=data/follower_train.csv --application-id=test --verbosity=3
```

For detailed usage, please refer to help:
```
python -m fedlearner.model.tree.trainer
```
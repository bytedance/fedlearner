# Federated GBDT Example

This example shows how to use fedlearner to train and test
two-party federated GBDT models on the MNIST dataset.

## Data

To run the the example, first prepare the data with:
```
python make_data.py --verify-example-ids=True
```
This will generate files in `data`.

The data files are CSV files with out header.
Each row contains float features (and labels) for a data example.
The first N columns are features for both leader and follower.
In `train` and `test` mode, the last column of leader's data file
contain labels (0 or 1). In `eval` mode there are no labels in the data.


## Training

You need to start two processes, one for leader and one for
follower, for each training task.

Run the following command to start leader:
```
python -m fedlearner.model.tree.trainer leader \
    --local-addr=localhost:50051 \
    --peer-addr=localhost:50052 \
    --data-path=data/leader_train.csv \
    --export-model-path=leader_model.proto \
    --verify-example-ids=true
```

Run the following command in another terminal session to start follower:
```
python -m fedlearner.model.tree.trainer follower \
    --local-addr=localhost:50052 \
    --peer-addr=localhost:50051 \
    --data-path=data/follower_train.csv \
    --export-model-path=follower_model.proto \
    --verify-example-ids=true
```

There are many modeling parameters you can change with additional
commandline arguments. Please refer to help for more info:
```
python -m fedlearner.model.tree.trainer
```

## Evaluation

Now you can load the previously trained model test its accuracy on test data.
This is similar to training except you need to set `mode` to `test`:

Run the following command to start leader:
```
python -m fedlearner.model.tree.trainer leader \
    --local-addr=localhost:50051 \
    --peer-addr=localhost:50052 \
    --mode=test \
    --data-path=data/leader_test.csv \
    --load-model-path=leader_model.proto \
    --verify-example-ids=true
```

Run the following command in another terminal session to start follower:
```
python -m fedlearner.model.tree.trainer follower \
    --local-addr=localhost:50052 \
    --peer-addr=localhost:50051 \
    --mode=test \
    --data-path=data/follower_test.csv \
    --load-model-path=follower_model.proto \
    --verify-example-ids=true
```

## Performance


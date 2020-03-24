# Quick Start with Fedlearner

To quickly run a simple training example locally:

```
cd example/mnist
python leader.py --local-addr=localhost:50051 --peer-addr=localhost:50052 --data-path=data/leader &
python follower.py --local-addr=localhost:50052 --peer-addr=localhost:50051 --data-path=data/follower/ &
```

For better display, run the last two commands in two different terminals.
# Quick Start with Fedlearner

## Install on local machine for testing

First clone the latest code of this library from github:

```
git clone https://github.com/piiswrong/fedlearner.git
```

Then setup python environment to run the package. Make sure that you have Python 3.6, other versions may have dependency issues:

```
cd fedlearner
pip install -r requirements.txt
export PYTHONPATH=$(PWD):$PYTHONPATH
```

If you see errors during gmpy2 installation, you may need to install the GMP library first. Try

```
apt-get install libgmp-dev libmpc-dev libmpfr-dev
```

## Run Example

To quickly run a simple training example locally:

```
cd example/mnist
python leader.py --local-addr=localhost:50051 --peer-addr=localhost:50052 --data-path=data/leader &
python follower.py --local-addr=localhost:50052 --peer-addr=localhost:50051 --data-path=data/follower/ &
```

For better display, run the last two commands in two different terminals.
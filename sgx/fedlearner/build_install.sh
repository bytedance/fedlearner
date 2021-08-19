set -e

cd ${FEDLEARNER_PATH}

make protobuf
make op

rm -rf dist
python3 setup.py bdist_wheel

pip3 uninstall -y fedlearner
pip3 install ./dist/*.whl
mkdir -p /usr/local/lib/python3.6/dist-packages/cc
cp ./cc/embedding.so /usr/local/lib/python3.6/dist-packages/cc

cd -

set -e

${GRPC_PATH}/build_python.sh

pip3 uninstall -y grpcio
pip3 install ${GRPC_PATH}/dist/*.whl

python3 -u -c "import grpc"

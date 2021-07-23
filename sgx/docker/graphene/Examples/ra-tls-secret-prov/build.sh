set -e

make -C ${GRAPHENEDIR}/Pal/src/host/Linux-SGX/tools/ra-tls dcap

cd ${GRAPHENEDIR}/Examples/ra-tls-secret-prov

make dcap pf_crypt

cd -

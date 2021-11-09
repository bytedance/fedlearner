set -e

#make -C ${GRAMINEDIR}/Pal/src/host/Linux-SGX/tools/ra-tls dcap

cd ${GRAMINEDIR}/CI-Examples/ra-tls-secret-prov

make dcap pf_crypt

cd -

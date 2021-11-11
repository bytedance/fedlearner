set -ex

export MBEDTLS_PATH=${GRAMINEDIR}/CI-Examples/ra-tls-mbedtls

cd ${MBEDTLS_PATH}

make clean
make app dcap

cp -r mbedtls/include ${INSTALL_PREFIX}

whereis libmbedtls_gramine libmbedcrypto_gramine libmbedx509_gramine 
whereis libsgx_util libsgx_dcap_quoteverify libdcap_quoteprov.so.*
whereis libra_tls_attest libra_tls_verify_dcap libra_tls_verify_epid

cd -

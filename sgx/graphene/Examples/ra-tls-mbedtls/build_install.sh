set -e

export QUOTE_VERIFY_PATH=${ISGX_DRIVER_PATH}/QuoteVerification
export GRAPHENE_RATLS_PATH=${GRAPHENEDIR}/Pal/src/host/Linux-SGX/tools/ra-tls
export MBEDTLS_PATH=${GRAPHENEDIR}/Examples/ra-tls-mbedtls


# rm -rf /usr/lib/x86_64-linux-gnu/libsgx_dcap_quoteverify.s*
# cp libsgx_dcap_quoteverify.s* from PCCS to /usr/lib/x86_64-linux-gnu

make -C ${GRAPHENE_RATLS_PATH} dcap

cd ${MBEDTLS_PATH}

make clean
make app dcap

cp -r ${MBEDTLS_PATH}/mbedtls/install/include ${INSTALL_PREFIX}
cp -r ${MBEDTLS_PATH}/mbedtls/install/lib/*.a ${INSTALL_PREFIX}/lib
cp -r ${MBEDTLS_PATH}/libs/* /usr/lib/x86_64-linux-gnu

whereis libmbedcrypto libmbedtls libmbedx509 
whereis libsgx_util libsgx_dcap_quoteverify libdcap_quoteprov.so.*
whereis libra_tls_attest libra_tls_verify_dcap libra_tls_verify_epid libra_tls_verify_dcap_graphene

ls -l /usr/lib/x86_64-linux-gnu/libsgx_dcap_quoteverify.so*
ls -l /usr/lib/x86_64-linux-gnu/libdcap_quoteprov.so*
ls -l /usr/lib/x86_64-linux-gnu/libsgx_default_qcnl_wrapper.so*

cd -

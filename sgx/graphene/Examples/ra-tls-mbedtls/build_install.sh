set -e

export QUOTE_VERIFY_PATH=${ISGX_DRIVER_PATH}/QuoteVerification
export MBEDTLS_PATH=${GRAPHENEDIR}/Examples/ra-tls-mbedtls

# rm -rf /usr/lib/x86_64-linux-gnu/libsgx_dcap_quoteverify.s*
# cp libsgx_dcap_quoteverify.s* from PCCS to /usr/lib/x86_64-linux-gnu

make -C ${GRAPHENEDIR}/Pal/src/host/Linux-SGX/tools/ra-tls dcap

cd ${MBEDTLS_PATH}

make clean
make app dcap

cp -r ${MBEDTLS_PATH}/mbedtls/install/include ${INSTALL_PREFIX}
cp -r ${MBEDTLS_PATH}/libs/* /usr/lib/x86_64-linux-gnu

ls -l /usr/lib/x86_64-linux-gnu/libsgx_dcap_quoteverify.s*

cd -

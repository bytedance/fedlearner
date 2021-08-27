set -e

export MBEDTLS_PATH=${GRAPHENEDIR}/Examples/ra-tls-mbedtls

# Build ra-tls-mbedtls
if [ ! -d "${MBEDTLS_PATH}/mbedtls" ]; then
    ${MBEDTLS_PATH}/build_install.sh
fi

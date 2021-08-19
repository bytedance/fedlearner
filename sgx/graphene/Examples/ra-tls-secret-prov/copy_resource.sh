#!/bin/bash
set -e

if  [ ! -n "$1" ] ; then
    target=.
else
    target=$1
fi

${GRAPHENEDIR}/Examples/ra-tls-secret-prov/build.sh

cp -r ${GRAPHENEDIR}/Examples/ra-tls-secret-prov/libs/* ${target}
cp -r ${GRAPHENEDIR}/Examples/ra-tls-secret-prov/pf_crypt ${target}

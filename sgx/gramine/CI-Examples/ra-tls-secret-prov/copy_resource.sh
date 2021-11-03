#!/bin/bash
set -e

if  [ ! -n "$1" ] ; then
    target=.
else
    target=$1
fi

${GRAMINEDIR}/Examples/ra-tls-secret-prov/build.sh

cp -r ${GRAMINEDIR}/CI-Examples/ra-tls-secret-prov/libs/* ${target}
cp -r ${GRAMINEDIR}/CI-Examples/ra-tls-secret-prov/pf_crypt ${target}

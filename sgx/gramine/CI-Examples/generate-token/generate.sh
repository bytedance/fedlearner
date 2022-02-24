#!/bin/bash
set -x

shopt -s expand_aliases
alias make_logfilter="grep \"mr_enclave\|mr_signer\|isv_prod_id\|isv_svn\""

rm -rf *.log
make clean && make | make_logfilter

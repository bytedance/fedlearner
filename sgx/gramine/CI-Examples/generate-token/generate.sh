#!/bin/bash
set -x

shopt -s expand_aliases
alias make_logfilter="grep -v 'measured'"
alias runtime_logfilter="grep -v 'FUTEX|measured|memory entry|cleaning up|async event|shim_exit'"

rm -rf *.log
make clean && make | make_logfilter

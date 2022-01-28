#!/bin/bash

pname=$1
PID=`ps -ef | grep $pname | awk '{print $2}'`
kill $PID

if [ -d "/pod-data/" ];then
    echo "exit" > "/pod-data/sidecar.txt"
fi

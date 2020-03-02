#!/bin/bash

cmd=$1
path="/etc/worker" #TODO: pass $path from parameter
if [[ -z $WORKER_ID ]];
then
	WORKER_ID=$POD_NAME
fi

pair="${path}/${WORKER_ID}"
while [ true ];
do
	if [[ -f ${pair} ]] && [[ -n "$(cat ${pair})" ]];
	then
		export REMOTE_IP=`cat ${pair}`
		break
	else
		sleep 1
	fi
done
exec ${cmd}

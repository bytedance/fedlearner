#!/bin/bash

cmd=$1
if [[ -z $WORKER_ID ]]; then
    pair="/etc/master/${MASTER_ID}"
else
    pair="/etc/worker/${WORKER_ID}"
fi

while [[ true ]]; do
	if [[ -f ${pair} ]] && [[ -n "$(cat ${pair})" ]]; then
		export PEER_ADDR=`cat ${pair}`
		break
	else
		echo "still waiting for peer addr"
		sleep 1
	fi
done
exec ${cmd}

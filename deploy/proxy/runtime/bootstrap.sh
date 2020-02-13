#!/bin/bash
CURDIR=$(cd `dirname $0`; pwd)

# If you modified this variable, don't forget to modity logfile in service.yml
LOG_DIR="$CURDIR/logs/"
if [ ! -d $LOG_DIR ]; then
    mkdir -p $LOG_DIR
fi

sed -i "s|xcur_dir|${CURDIR}|g" ${CURDIR}/configs/nginx.conf

exec ${CURDIR}/bin/nginx -c ${CURDIR}/configs/nginx.conf -p ${CURDIR}

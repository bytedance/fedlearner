#!/bin/bash

set -ex

urlencode() {
    # urlencode <string>

    old_lc_collate=$LC_COLLATE
    LC_COLLATE=C

    local length="${#1}"
    i=0
    while [ "$i" -lt "$length" ]; do
        local c="${1:$i:1}"
        case $c in
            [a-zA-Z0-9.~_-]) printf '%s' "$c" ;;
            *) printf '%%%02X' "'$c" ;;
        esac
        i=$(( i + 1 ))
    done

    LC_COLLATE=$old_lc_collate
}

ENCODE_DB_PASSWORD=`urlencode ${DB_PASSWORD:-fedlearner}`

npx sequelize-cli db:migrate \
    --url="${DB_DIALECT:-mysql}://${DB_USERNAME:-fedlearner}:${ENCODE_DB_PASSWORD}@${DB_HOST:-127.0.0.1}:${DB_PORT:-3306}/${DB_DATABASE:-fedlearner}"

node bootstrap.js &

while true; do sleep 1000; done

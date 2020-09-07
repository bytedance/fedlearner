#!/bin/bash

set -ex

npx sequelize-cli db:migrate \
    --url="${DB_DIALECT:-mysql}://${DB_USERNAME:-fedlearner}:${DB_PASSWORD:-fedlearner}@${DB_HOST:-127.0.0.1}:${DB_PORT:-3306}/${DB_DATABASE:-fedlearner}"

node bootstrap.js

while true; do sleep 1m; done

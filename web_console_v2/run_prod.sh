#!/bin/bash

set -e

service nginx restart

code-server &

# Starts API server
cd /app/api
sh run_prod.sh --migrate

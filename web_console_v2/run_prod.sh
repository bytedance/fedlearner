#!/bin/bash

set -e

service nginx restart

# Starts API server
cd /app/api
sh run_prod.sh --migrate

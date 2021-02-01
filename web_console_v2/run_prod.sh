#!/bin/bash

set -e

service nginx restart

# Starts API server
cd api
sh run_prod.sh
